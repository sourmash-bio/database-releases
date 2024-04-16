# run batches of info download if needed

for ((i=1; i<=1000; i++))
do
    echo "Starting batch #${i} of 1000"
    # each takes ~ 5-8 mins
    sbatch --partition=low2 --time=15:00 --cpus-per-task=1 --nodes=1 --mem=1000 \
    --job-name=${i}_batch --chdir=/home/ntpierce/database-releases/gtdb-rs214.protein \
    --wrap="module load conda; conda activate release-gtdb-rs214; \
    snakemake download_and_build --profile default -c 1 --batch build_fromfile_from_assemblyinfo=${i}/1000 --nolock"
    
    # only submit 100 jobs simultaneously
    if ((i % 100 == 0)); then
        echo "Waiting for 8 minutes..."
        sleep 8m
    fi
done