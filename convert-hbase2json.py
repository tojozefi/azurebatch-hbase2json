from __future__ import print_function
import sys
import math
import datetime
import config

import azure.storage.blob as azureblob
import azure.batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels


def generate_blob_name_list(container_client, prefix):
    blob_list = container_client.list_blobs(name_starts_with=prefix)
    blob_name_list = []
    for blob in blob_list:
        blob_name_list.append(blob.name)
    return blob_name_list
    
    
def create_job(batch_client, job_name, blob_name_list):
    print('Creating job [{}]...'.format(job_name))
    batch_client.job.add(
        batchmodels.JobAddParameter(
            id=job_name,
            pool_info=batchmodels.PoolInformation(
#                pool_id=config._POOL_ID,
                auto_pool_specification=batchmodels.AutoPoolSpecification(
                    pool_lifetime_option='job',
                    keep_alive=False,
                    pool=batchmodels.PoolSpecification(
                        vm_size=config._POOL_VM_SIZE,
                        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
                            image_reference=batchmodels.ImageReference(
                                publisher="Canonical",
                                offer="UbuntuServer",
                                sku="18.04-LTS",
                                version="latest"
                            ),
                            node_agent_sku_id="batch.node.ubuntu 18.04"
                        ),
                        max_tasks_per_node=config._TASKS_PER_NODE,
                        target_dedicated_nodes=min(math.ceil(len(blob_name_list)/config._TASKS_PER_NODE),config._MAX_NODES),
                        start_task=batchmodels.StartTask(
                            command_line="/bin/bash -c 'apt-get update; apt-get install -y openjdk-11-jre-headless'",
                            wait_for_success=True,
                            user_identity=batchmodels.UserIdentity(
                                auto_user=batchmodels.AutoUserSpecification(
                                    scope=batchmodels.AutoUserScope.pool,
                                    elevation_level=batchmodels.ElevationLevel.admin)
                            )
                        )
                    )
                )
            )
        )
    )
    
    
def add_tasks(batch_client, job_name, blob_name_list, input_container_client, output_container_client):
    print('Adding {} tasks to job [{}]...'.format(len(blob_name_list), job_name))
    
    task_list = []
    id=0
    for blob_path in blob_name_list: 
        print(' task {} for converting blob {}...'.format(id,blob_path))
        blob_name = blob_path.split('/')[-1]
        input_container_uri,sas_token = config._INPUT_CONTAINER_URL.split('?',1)
        blob_url = "{}/{}?{}".format(input_container_uri, blob_path, sas_token)
        task_list.append(
            batchmodels.TaskAddParameter(
                id=str(id),
                display_name=blob_path,
                command_line="/bin/bash -c 'mkdir output; java -jar {} --sourceFile={} --destinationPath=output'".format(config._JAR_FILE,blob_name),
                resource_files=[
                    batchmodels.ResourceFile(auto_storage_container_name=config._JAR_CONTAINER),
                    batchmodels.ResourceFile(http_url=blob_url,file_path=blob_name)
                ],
                output_files=[
                    batchmodels.OutputFile(
                        file_pattern='../std*.txt',
                        destination=batchmodels.OutputFileDestination(
                            container=batchmodels.OutputFileBlobContainerDestination(
                                container_url=config._OUTPUT_CONTAINER_URL,
                                path='/'.join([job_name,'logs',blob_name])
                            )
                        ),
                        upload_options=batchmodels.OutputFileUploadOptions(
                            upload_condition=batchmodels.OutputFileUploadCondition.task_completion)
                    ),
                    batchmodels.OutputFile(
                        file_pattern='output*.json',
                        destination=batchmodels.OutputFileDestination(
                            container=batchmodels.OutputFileBlobContainerDestination(
                                container_url=config._OUTPUT_CONTAINER_URL,
                                path='/'.join([job_name,blob_path])
                            )
                        ),
                        upload_options=batchmodels.OutputFileUploadOptions(
                            upload_condition=batchmodels.OutputFileUploadCondition.task_completion)
                    )
                ],
                constraints=batchmodels.TaskConstraints(
                    retention_time=datetime.timedelta(seconds=1)
                )
            )
        )
        id+=1
        
    batch_client.task.add_collection(job_name, task_list)

    #patch job property on_all_tasks_complete=terminate_job
    job = batch_client.job.get(job_id=job_name) 
    batch_client.job.patch(
        job_id=job_name,
        job_patch_parameter=batchmodels.JobPatchParameter(
            on_all_tasks_complete=batchmodels.OnAllTasksComplete.terminate_job
        )
    )



if __name__ == '__main__':

    if len(sys.argv)<2:
        print("Syntax: {} <jobname> [<prefix>]".format(sys.argv[0]),file=sys.stderr)
        print(" <jobname>: Batch job name")
        print(" <prefix>: input prefix filter (optional)")
        sys.exit(1)

    job_name = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv)>2 else None 

    # Create the container clients (container_url must include SAS token)
    input_container_client = azureblob.ContainerClient.from_container_url(container_url=config._INPUT_CONTAINER_URL)
    output_container_client = azureblob.ContainerClient.from_container_url(container_url=config._OUTPUT_CONTAINER_URL)

    # Create a Batch service client. 
    batch_client = azure.batch.BatchServiceClient(
        credentials = batchauth.SharedKeyCredentials(account_name=config._BATCH_ACCOUNT_NAME, key=config._BATCH_ACCOUNT_KEY), 
        batch_url=config._BATCH_ACCOUNT_URL)

    blob_name_list = generate_blob_name_list(input_container_client, prefix)

    # Create the job that will run the tasks.
    create_job(batch_client, job_name, blob_name_list)

    # Add the tasks to the job. 
    add_tasks(batch_client, job_name, blob_name_list, input_container_client, output_container_client)

    print('Converter job [{}] launched'.format(job_name))
    print('Monitor the job status in https://portal.azure.com or Batch Explorer.')
    
