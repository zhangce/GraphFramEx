#!/bin/bash

#SBATCH --time=600
#SBATCH --gpus-per-task=2
#SBATCH --mem=5000
#SBATCH --output=/cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/logs/_edge_size=1_explainer_name=gnnexplainer.stdout
#SBATCH --error=/cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/logs/_edge_size=1_explainer_name=gnnexplainer.stderr
#SBATCH --job-name=gnnexplainer_size_edge_size=1_explainer_name=gnnexplainer
#SBATCH --open-mode=append
#SBATCH --signal=B:USR1@120

cd .
EXP_NUMBER=$SLURM_ARRAY_TASK_ID
export JOBNAME="gnnexplainer_size_edge_size=1_explainer_name=gnnexplainer"
LOG_STDOUT="/cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/logs/_edge_size=1_explainer_name=gnnexplainer.stdout"
LOG_STDERR="/cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/logs/_edge_size=1_explainer_name=gnnexplainer.stderr"

trap_handler () {
   echo "Caught signal" >> $LOG_STDOUT
   sbatch --begin=now+120 /cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/run_edge_size=1_explainer_name=gnnexplainer.sh
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
PYTHONUNBUFFERED=yes MKL_THREADING_LAYER=GNU python code/main.py \
--edge_size 1 --explainer_name gnnexplainer --dataset syn1 --num_test 100 --data_save_dir data --explain_graph False --dest /cluster/home/kamara/Explain/checkpoints/gnnexplainer_size/_edge_size=1_explainer_name=gnnexplainer >> $LOG_STDOUT 2>> $LOG_STDERR && echo 'JOB_FINISHED' >> $LOG_STDOUT &
wait $!
