#!/bin/bash

#SBATCH --gpus-per-task=1
#SBATCH --mem=5000
#SBATCH --output=/cluster/home/kamara/Explain/checkpoints/sparsity/logs/_sparsity=0.7_dataset=syn6.stdout
#SBATCH --error=/cluster/home/kamara/Explain/checkpoints/sparsity/logs/_sparsity=0.7_dataset=syn6.stderr
#SBATCH --job-name=sparsity_sparsity=0.7_dataset=syn6
#SBATCH --open-mode=append
#SBATCH --signal=B:USR1@120

cd .
EXP_NUMBER=$SLURM_ARRAY_TASK_ID
export JOBNAME="sparsity_sparsity=0.7_dataset=syn6"
LOG_STDOUT="/cluster/home/kamara/Explain/checkpoints/sparsity/logs/_sparsity=0.7_dataset=syn6.stdout"
LOG_STDERR="/cluster/home/kamara/Explain/checkpoints/sparsity/logs/_sparsity=0.7_dataset=syn6.stderr"

trap_handler () {
   echo "Caught signal" >> $LOG_STDOUT
   sbatch --begin=now+120 /cluster/home/kamara/Explain/checkpoints/sparsity/run_sparsity=0.7_dataset=syn6.sh
   exit 0
}
function ignore {
   echo "Ignored SIGTERM" >> $LOG_STDOUT
}

trap ignore TERM
trap trap_handler USR1
echo "Git hash:" >> $LOG_STDOUT
echo $(git rev-parse HEAD 2> /dev/null) >> $LOG_STDOUT

which python >> $LOG_STDOUT
echo "---Beginning program ---" >> $LOG_STDOUT
PYTHONUNBUFFERED=yes MKL_THREADING_LAYER=GNU python exp_synthetic/main.py \
--explainer_name subgraphx --sparsity 0.7 --dataset syn6 --num_test_nodes 100 --data_save_dir data --gpu True --dest /cluster/home/kamara/Explain/checkpoints/sparsity/_sparsity=0.7_dataset=syn6 >> $LOG_STDOUT 2>> $LOG_STDERR && echo 'JOB_FINISHED' >> $LOG_STDOUT &
wait $!