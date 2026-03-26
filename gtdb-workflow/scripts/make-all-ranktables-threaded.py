#! /usr/bin/env python

import os
import argparse
from sourmash_plugin_pangenomics import pangenome_ranktable_main
import sourmash_utils
from sourmash import sourmash_args
from concurrent.futures import ProcessPoolExecutor, as_completed

def sanitize(name):
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in name)

def work_generator(db, args):
    for n, ss in enumerate(db.signatures()):
        sig_name = ss.name
        sanitized = sanitize(sig_name)
        out_csv = os.path.join(args.outdir, f"gtdb-rs{args.release}-k{args.ksize}.{args.rank}.{sanitized}.csv")
        out_csv_gz = out_csv + ".gz"

        per_sig_kwargs = vars(args).copy()
        per_sig_kwargs.update({
            "lineage": sig_name,
            "output_hash_classification": out_csv,
        })

        yield {
            "per_sig_kwargs": per_sig_kwargs,
            "out_csv": out_csv,
            "out_csv_gz": out_csv_gz,
            "sig_name": sig_name,
        }

def process_signature(args_dict):
    per_sig_kwargs = args_dict["per_sig_kwargs"]
    out_csv = args_dict["out_csv"]
    out_csv_gz = args_dict["out_csv_gz"]
    sig_name = args_dict["sig_name"]

    if os.path.exists(out_csv) or os.path.exists(out_csv_gz):
        return f"Skipping {out_csv} or {out_csv_gz}: file already exists."
    
    pangenome_ranktable_main(argparse.Namespace(**per_sig_kwargs))
    return f"Processed {sig_name}"

def main():
    p = argparse.ArgumentParser()

    p.add_argument("data", help="sourmash signature database zip file")
    p.add_argument("--outdir", default="ranktables", help="Directory for output CSV files")
    p.add_argument("-i", "--ignore-case", action="store_true")
    p.add_argument("--release", type=str, default=None)
    p.add_argument("--rank", type=str, default=None)
    p.add_argument("--gzip", action="store_true")
    p.add_argument("--threads", type=int, default=1, help="Number of threads/processes for parallel processing")

    sourmash_utils.add_standard_minhash_args(p)

    args = p.parse_args()

    # Select minhash args
    select_mh = sourmash_utils.create_minhash_from_args(args)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"loading sketches from file '{args.data}'")
    db = sourmash_utils.load_index_and_select(args.data, select_mh)
    print(f"'{args.data}' contains {len(db)} signatures")


    # Parallel processing
    if args.threads > 1:
        with ProcessPoolExecutor(max_workers=args.threads) as executor:
            work_iter = work_generator(db, args)
            futures = {executor.submit(process_signature, w): w["sig_name"] for w in work_iter}
            for future in as_completed(futures):
                print(future.result())
    # Single-threaded fallback
    else:
        for i, w in enumerate(work, 1):
            msg = process_signature(w)
            print(f"[{i}/{len(work)}] {msg}")

if __name__ == "__main__":
    main()
