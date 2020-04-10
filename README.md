# Azure Batch HBASE to JSON converter
This repository offers Azure Batch templates to run parallel convertion jobs from HBASE sequence file to JSON format. 

## Prerequisites
1. Azure [subscription](https://azure.microsoft.com/en-us/) 
2. Azure [Batch account](https://azure.microsoft.com/en-us/services/batch/) and a linked [blob storage](https://azure.microsoft.com/en-us/services/storage/blobs/) account.  
 See [here](https://docs.microsoft.com/en-us/azure/batch/batch-account-create-portal) for instructions how to create a Batch account.
3. Core quota for [H-series VMs](https://docs.microsoft.com/en-us/azure/virtual-machines/h-series) in your Batch account.  
 See [here](https://docs.microsoft.com/en-us/azure/batch/batch-quota-limit#increase-a-quota) for instructions how to request quota increase in your Batch account.  
4. [Batch Explorer](https://azure.github.io/BatchExplorer/) application installed on your local PC.

## Procedure

### I. Creating Batch pool from template
1. Open Batch Explorer and login to your Azure account when prompted.
2. Select your Batch account in *Dashboard* tab:
![batch-explorer-dashboard](screenshots/batch-explorer-dashboard.png)
3. Go to *Gallery* tab and click *Pick a local template* button:
![gallery-picklocaltemplate](screenshots/gallery-picklocaltemplate.png)
4. Select *sequencer-pool.json* template (you need to download it first to your local system from [here](https://github.com/tojozefi/azurebatch-hbase2json/raw/master/sequencer-pool.json))
![run-pool-template](screenshots/run-pool-template.png)
Pool template parameters description:
 - *pool* - pool name, must be unique within the Batch account
 - *vm count* - number of VMs to deploy in the pool. Should be equal to rounded-up quotient *nr of files to process* / *tasks per node* (see the next parameter).  
 Note: The hardcoded and recommended VM size for hbase2json converter job is [Standard_H16](https://docs.microsoft.com/en-us/azure/virtual-machines/h-series).
 - *tasks per node* - Maximum number of tasks allowed to run in parallel per node. The default value is 16 (equal to the amount of cores on H16 VM). Depending on your data size ou may need to reduce it so that the anticipated size of input HBASE and output JSON data fits on the VM local disk (2 TB).
 
Provide the pool parameter values or accept the defaults and click *Create and close* button.

The pool deployment process will start. You should now be able to see and manage your pool in *Pools* tab: 
![pool-deployment](screenshots/pool-deployment.png)

### II. Preparing file-group containers for running convertion jobs
1. Goto *Data* tab and click '+' icon to create a new empty file group:
![data-filegroup-createempty](screenshots/data-filegroup-createempty.png)
Provide a name for the input data file group (the default name is *sequencer-input*).

2. Create two more empty file groups: for job assets (*sequencer-job*) and for job outputs (*sequencer-output*):
![data-filegroups](screenshots/data-filegroups.png)

3. Upload input files to *sequencer-input* file-group container, e.g. by drag&dropping them from the system File Explorer:
![sequencer-input-dragndrop](screenshots/sequencer-input-dragndrop.png)
 
4. Upload the code JAR file to *sequencer-code* file-group container:
![sequencer-code-dragndrop](screenshots/sequencer-code-dragndrop.png)

You are now ready to run the HBASE-to-JSON conversion jobs. 


### III. Running the job from template  
1. Go to *Gallery* tab and click *Pick a local template* button:
![gallery-picklocaltemplate](screenshots/gallery-picklocaltemplate.png)
4. Select *sequencer-job.json* template (you need to download it first to your local system from [here](https://github.com/tojozefi/azurebatch-hbase2json/raw/master/sequencer-job.json))
![run-job-template](screenshots/run-job-template.png)
In the template parameter window select your pool and provide the parameters:
 - *job name* - must be unique within the Batch account
 - *JAR file* - name of the JAR file that you've uploaded to *sequencer-code* file-group container and want to use for job execution
 - *input filegroup* - name of file-group container with input files (sequencer-input)  
 - *asset filegroup* - name of file-group container with JAR file (sequencer-code)
 - *output filegroup* - name of file-group container for job outputs (sequencer-output)

 Click *Run and close* button to start the job.

### IV. Monitoring the job
After the job is started you should see it in *Jobs* tab with all the tasks that have been created to process files from the input filegroup container:
![job-view](screenshots/job-view.png)

By clicking on the pool link in the job view you can jump to the view of your pool in *Pools* tab.  
You can also click on each task in the job view to dig into task details in the task view:
![pool-view](screenshots/pool-view.png)
 
You can follow task progress e.g. by opening its stdout stream in *stdout.txt* file:
![task-view](screenshots/task-view.png)

After the job is finished you will find job outputs in *Data* tab, persisted in the output filegroup container, under the virtual folder with the job's name:
![job-output](screenshots/job-output.png)

### V. Deallocating billable compute resources
After you're done with running the jobs, don't forget to delete your pool or resize it to zero nodes in *Pools* tab:
![pool-delete-resize](screenshots/pool-delete-resize.png)

You can order resizing pool to zero nodes while your tasks are still running so that the pool will get resized automatically right after the job completion:
![pool-resize-running](screenshots/pool-resize-running.png)

![pool-resize-taskcompletion](screenshots/pool-resize-taskcompletion.png)

You might also consider using pool [autoscaling](https://docs.microsoft.com/en-us/azure/batch/batch-automatic-scaling) to automate pool size management.
