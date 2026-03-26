#! /usr/bin/env python

import argparse
import re
import os
import pandas as pd
from multiprocessing import Process, Manager

# include a restore paths for after benchmarking the rules with wildcards that nest the benchmark file i.e. have a / in the wildcard
# last bit would be to add a config file parser to include custom resources into the file
def main():
    p = argparse.ArgumentParser(prog='name', description='{name} will do what I describe here')

    p.add_argument('-s', '--snakefile', required=True, help='The snakefile to bless with benchmark/resource sections')
    p.add_argument('-o', '--output', help='New snakefile with benchmark sections') #Should this be set to required=True?
    p.add_argument('-t', '--top-level', action='store_true', help='Print the snakefile top-level/psuedo-rules rules (e.g. rule all)')
    p.add_argument('-tr', '--target-rule', nargs='?', type=str, default=None, const='all', help='Return onlt the target rule text. Default will return all target rule text.')
    p.add_argument('-w', '--wildcards', action='store_true', help='Print the wildcards in benchmark file name for each target rule')
    p.add_argument('-ew', '--exclude-wildcards', action='extend', nargs='+', type=str, help='Include any wildcards that should be excluded from the benchmark filename (e.g. {outdir} or {{indir}})')
    p.add_argument('-b', '--benchmarks', type=check_positive, nargs='?', const=1, metavar='1,2,3, or ...', help='''Add benchmark sections to each target rule in the snakefile.
            Set any number of repeats for all benchmarks with a positive integer''')
    p.add_argument('-rb', '--remove-benchmarks', action='store_true', help='Remove all benchmark sections from the input file!')
    p.add_argument('-r', '--resources', action='store_true', help='Add resources section to each target rule in snakefile from benchmark tsv output')
    p.add_argument('-rr', '--remove-resources', action='store_true', help='Remove all resource sections from the input file!')
    p.add_argument('-v', '--verbose', action='store_true', help='Print current state of benchmarks and resources section in file.')

    args = p.parse_args()

    benchmark_count = args.benchmarks
    snakefile = args.snakefile
    output = args.output
    top_level = args.top_level
    target_rule = args.target_rule
    wildcard = args.wildcards
    exclude_wildcards = args.exclude_wildcards
    remove_benchmarks = args.remove_benchmarks
    resources = args.resources
    remove_resources = args.remove_resources
    verbose = args.verbose

    with open(snakefile, 'r') as fp:
        data = fp.read()

    # Part of main for rules, benchmarks, wildcards, resources data collection
    all_rules = re.findall(r'rule (.+):', data)
    if all_rules:
        print("\nFound rules:", all_rules)

        manager = Manager()

        rule_data = manager.dict()
        new_rule_data = manager.dict()
        wildcard_data = manager.dict()
        top_level_rules = manager.list()
        processes = []

        ## resources are defined for output file
############I think this should become a function called in process_rule()
        if resources:
            apath = os.path.abspath(snakefile)
            filepath, filename = os.path.split(apath)
            inputpath = filepath + "/benchmarks"

            combined_tsvs = "benchmarks.all.lines.tsv"
            full_report = "benchmarks.full.report.tsv"
            concise_report = "benchmarks.concise.report.tsv"

            combine_tsvs(inputpath, combined_tsvs)

            grouped_data, concise_data = calculate_values(combined_tsvs)
             #s_max = concise_data[['s_max']].values.tolist()
             #max_rss_max = concise_data[['max_rss_max']].values.tolist()

             #print(s_max)
             #print(max_rss_max)

            resource_values = concise_data.to_dict('index')
            print(resource_values)

        else:
             # A placeholder for the process function to operate when the -r is not used
            resource_values = {}
############

        for rule_name in all_rules:
            process = Process(target=process_rule, args=(
                rule_name, data, rule_data, new_rule_data, remove_benchmarks, benchmark_count, wildcard_data, exclude_wildcards, top_level_rules, target_rule, resources, remove_resources, resource_values, verbose
                ))
            process.start()
            processes.append(process)

        for process in processes:
            process.join()

        # Part of main for returning the information to the user
        #For wildcard info
        if wildcard_data:
            if wildcard:
                for rule_name, wildcards_dict in wildcard_data.items():
                    wildcards = wildcards_dict.get('wildcards', [])
                    print(f"\nWildcards found in '{rule_name}': {wildcards}")
            if exclude_wildcards:
                for rule_name, wildcards_dict in wildcard_data.items():
                    using = wildcards_dict.get('using', [])
                    removed = wildcards_dict.get('removed', [])
                    original = wildcards_dict.get('original', [])
                    if not using:
                        print(f"\nAll wildcards have been excluded for '{rule_name}'")
                    else:
                        print(f"\nOriginal wildcards found in {rule_name}: {original}\nRemoved wildcards from '{rule_name}': {removed}\nRemaining wildcards in '{rule_name}': {using}")
        else:
            if wildcard:
                print("\nNo wildcards found!")
            if exclude_wildcards:
                print("\nNo wildcards found!")

        #For top_level rule info
        if top_level and top_level_rules:
            for rule in top_level_rules:
                print(f"\nRule '{rule}' is a top-level/psuedo rule")
        elif top_level and not top_level_rules:
            print("\nNo top-level/psuedo rules found!")

        # For source output files
        if resources:
             # Add 'filename' as a separate column in the resulting DataFrame
             grouped_data.reset_index(inplace=True)
             concise_data.reset_index(inplace=True)

             col0 = grouped_data.pop('filename')
             grouped_data.insert(len(grouped_data.columns), 'filename', col0)
             col0 = concise_data.pop('filename')
             concise_data.insert(len(concise_data.columns), 'filename', col0)

             grouped_data.to_csv(full_report, sep='\t')
             concise_data.to_csv(concise_report, sep='\t')

        ## For the output file
        for rule_name, rule_data_dict in new_rule_data.items():
            #print('zzz', (rule_name,), 'zzz2')
            rule_text = rule_data[rule_name]
            #print('xxx', (rule_text,), 'xxx2')
            benchmark_rule_text = rule_data_dict.get('benchmarks', {})
            #print('aaa', (benchmark_rule_text,), 'aaa2')
            resources_rule_text = rule_data_dict.get('resources', {})
            #print('bbb', (resources_rule_text,), 'bbb2')
            if 'benchmarks' in rule_data_dict and 'resources' in rule_data_dict:
                data = data.replace(rule_text, benchmarks_rule_text)
             #   print('ccc', (data,), 'ccc2')
                data = data.replace(data, resources_rule_text)
             #   print('ddd', (data,), 'ddd2')
            elif 'benchmarks' in rule_data_dict:
                data = data.replace(rule_text, benchmark_rule_text)
             #   print('fff', (data,), 'fff2')
            elif 'resources' in rule_data_dict:
                data = data.replace(rule_text, resources_rule_text)


        if output:
            with open(output, 'w') as output_fp:
                output_fp.write(data)

            if benchmark_count is not None or remove_benchmarks or resources or remove_resources:
                print("\nDone! Output saved and additional actions taken.")
            else:
                print("\nDone! Output saved without any additional actions.")
        else:
            print("\nDone! No output was given and nothing has been saved.")



def process_rule(rule_name, data, rule_data, new_rule_data, remove_benchmarks, benchmark_count, wildcard_data, exclude_wildcards, top_level_rules, target_rule, resources, remove_resources, resource_values, verbose):

    target_rule_pattern = rf'(?<=\nrule\s){rule_name}:((\n(.+))+)\s+output:((\n(.+))+)(?=\s\s\s\s+shell:|\s\s\s\s+run:|\s\s\s\s+script:)'
    output_pattern = r'(?<=output:)([\s\S]*?)(?=\n\s*\w+:|\Z)'
    benchmark_pattern = r'(\n[\s]*?benchmark:[\s\S]*?)(?=\n\s*\w+:|\Z)'
    resources_pattern = r'(\n[\s]*?resources:[\s\S]*?)(?=\n\s*\w+:|\Z)'
    wildcard_pattern = r'([{]{1,2}.+?[}]{1,2})' # internal parentheses arounf (.+?) will create a list of unbraced {} values

    rule_match = re.search(target_rule_pattern, data)

    if rule_match:
        rule_text = rule_match.group(0)
        rule_data[rule_name] = rule_text

        if target_rule == 'all':
            print(rule_text)
        elif target_rule == rule_name:
            print(rule_text)
        # For finding wildcards in the output section of a snakefile
        output_section = re.search(output_pattern, rule_text)
        wildcards = set(re.findall(wildcard_pattern, output_section.group(0)))

        if exclude_wildcards:
            using_wildcards = wildcards.difference(set(exclude_wildcards))
            removed_wildcards = wildcards.intersection(set(exclude_wildcards))
            wildcard_data[rule_name] = {'using': using_wildcards, 'removed': removed_wildcards, 'original': wildcards}
            benchmark_wildcards = '.'.join(f"{wc}" for wc in using_wildcards)
        else:
            wildcard_data[rule_name] = {'wildcards': wildcards}
            benchmark_wildcards = '.'.join(f"{wc}" for wc in wildcards)

        # Strings to add to rule_text
        formatted_benchmark_section = f"\n    benchmark:\n        f'benchmarks/{rule_name}.{benchmark_wildcards}.tsv'"
        benchmark_section = f"\n    benchmark:\n        'benchmarks/{rule_name}.{benchmark_wildcards}.tsv'"
        repeat_formatted_benchmark_section = f"\n    benchmark:\n        repeat(f'benchmarks/{rule_name}.{benchmark_wildcards}.tsv', {benchmark_count})"
        repeat_benchmark_section = f"\n    benchmark:\n        repeat('benchmarks/{rule_name}.{benchmark_wildcards}.tsv', {benchmark_count})"

#        # Adding benchmark section
#        if benchmark_count==1 and 'benchmark:' not in rule_text:
#            if any('{{' in wc for wc in benchmark_wildcards):
#                updated_rule_text = rule_text + formatted_benchmark_section
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#                print(f"\nAdded benchmark section to rule '{rule_name} with {benchmark_count} repeat")
#            else:
#                updated_rule_text = rule_text + benchmark_section
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#                print(f"\nAdded benchmark section to rule '{rule_name} with {benchmark_count} repeat")
#        elif isinstance(benchmark_count, int) and 'benchmark:' not in rule_text:
#            if any('{{' in wc for wc in benchmark_wildcards):
#                updated_rule_text = rule_text + repeat_formatted_benchmark_section
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#                print(f"\nAdded benchmark section to rule '{rule_name} with {benchmark_count} repeats")
#            else:
#                updated_rule_text = rule_text + repeat_benchmark_section
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#                print(f"\nAdded benchmark section to rule '{rule_name} with {benchmark_count} repeats")
#        elif benchmark_count is not None and 'benchmark:' in rule_text:
#            if remove_benchmarks:
#                print(f"\nRemoving benchmark section from rule '{rule_name}'")
#                updated_rule_text = re.sub(benchmark_pattern, '', rule_text)
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#            else:
#                print(f"\nBenchmark section already exists for rule '{rule_name}'")
#        elif benchmark_count is None and 'benchmark:' in rule_text:
#            if remove_benchmarks:
#                print(f"\nRemoving benchmark section from rule '{rule_name}'")
#                updated_rule_text = re.sub(benchmark_pattern, '', rule_text)
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#            else:
#                print(f"\nBenchmark section exists for rule '{rule_name}'")
#        elif benchmark_count is None and 'benchmark:' not in rule_text:
#            if remove_benchmarks:
#                print(f"\nNo benchmark section to remove from rule '{rule_name}'")
#                updated_rule_text = re.sub(benchmark_pattern, '', rule_text)
#                rule_data[rule_name] = rule_text
#                new_rule_data[rule_name] = updated_rule_text
#            else:
#                print(f"\nNo benchmark section exists for rule '{rule_name}'")
#        # Create a resources section
#        if resources and 'resources:' not in rule_text:
#            updated_rule_text = rule_text
#        # No -b or -r included in the cli or no target rules were in the file
#        elif benchmark_count is not None and resources is True:
#            print("\nNo target rules found! No place to add content!")
#    #rule don't match the target_rule_pattern and therefore must be a psuedo rule
#    else:
#        top_level_rules.append(rule_name)

        # Adding and removing benchmark section
        if 'benchmark:' in rule_text:
            if benchmark_count is not None:
                if remove_benchmarks:
                    print(f"\nRemoving benchmark section from rule '{rule_name}'")
                    updated_rule_text = re.sub(benchmark_pattern, '', rule_text)
                    if benchmark_count == 1:
                        print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeat")
                        if '{{' or 'f"' or "f'" in benchmark_wildcards:
                            updated_rule_text = updated_rule_text + formatted_benchmark_section
                        else:
                            updated_rule_text = updated_rule_text + benchmark_section
                    else:
                        print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeats")
                        #if '{{' in benchmark_wildcards:
                        if '{{' or 'f"' or "f'" in benchmark_wildcards:
                            updated_rule_text = updated_rule_text + formatted_benchmark_section
                            updated_rule_text = updated_rule_text + repeat_formatted_benchmark_section
                        else:
                            updated_rule_text = updated_rule_text + repeat_benchmark_section
                    new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
                elif verbose:
                    print(f"\nBenchmark section already exists for rule '{rule_name}'")
            else:
                if remove_benchmarks:
                    print(f"\nRemoving benchmark section from rule '{rule_name}'")
                    updated_rule_text = re.sub(benchmark_pattern, '', rule_text)
                    new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
                elif verbose:
                    print(f"\nBenchmark section exists for rule '{rule_name}'")
        else:
            if benchmark_count == 1:
                #if '{{' in benchmark_wildcards:
                if '{{' or 'f"' or "f'" in benchmark_wildcards:
                    updated_rule_text = rule_text + formatted_benchmark_section
                else:
                    updated_rule_text = rule_text + benchmark_section
                new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
                print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeat")
            elif benchmark_count is not None:
                #  if '{{' in benchmark_wildcards:

                if '{{' or 'f"' or "f'" in benchmark_wildcards:
                    updated_rule_text = rule_text + repeat_formatted_benchmark_section
                else:
                    updated_rule_text = rule_text + repeat_benchmark_section
                new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
                print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeats")
            elif verbose:
                print(f"\nNo benchmark section to remove from rule '{rule_name}'")
                new_rule_data[rule_name] = {'benchmarks': rule_text}


        if resources:
            for filename, resources_dict in resource_values.items():

                max_rss_max = resources_dict.get('max_rss_max', [])
                s_max = resources_dict.get('s_max', [])


            if filename == rule_name:
                resources_section = f"\n    resources:\n        mem_mb = lambda wildcards, attempt: {max_rss_max} * attempt,\n        runtime = lambda wildcards, attempt: ({s_max} / 60) * attempt,"

            else:
                resources_section = ""
                print(f'{filename} from concise benchmarks report does not equal {rule_name}!')

        if 'resources:' in rule_text:
            if resources is True:
                if remove_resources:
                    print(f"\nRemoving resources section from rule '{rule_name}'")
                    updated_rule_text = re.sub(resources_pattern, '', rule_text)
                   # if benchmark_count == 1:
                   #     print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeat")
                   #     if any('{{' in wc for wc in benchmark_wildcards):
                   #         updated_rule_text = updated_rule_text + formatted_benchmark_section
                   #     else:
                   #         updated_rule_text = updated_rule_text + benchmark_section
                   # else:
                   #     print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeats")
                   #     if any('{{' in wc for wc in benchmark_wildcards):
                   #         updated_rule_text = updated_rule_text + repeat_formatted_benchmark_section
                   #     else:
                   #         updated_rule_text = updated_rule_text + repeat_benchmark_section
                    print(f"And adding {max_rss_max} mem_mb and {s_max} runtime to '{rule_name}'")
                    updated_rule_text = updated_rule_text + resources_section
                    new_rule_data[rule_name] = {'resources': updated_rule_text}
                elif verbose:
                    print(f"\nResources section already exists for rule '{rule_name}'")
            else:
                if remove_resources:
                    print(f"\nRemoving resources section from rule '{rule_name}'")
                    updated_rule_text = re.sub(resources_pattern, '', rule_text)
                    new_rule_data[rule_name] = {'resources': updated_rule_text}
                elif verbose:
                    print(f"\nResources section exists for rule '{rule_name}'")
        else:
           # if benchmark_count == 1:
           #     if any('{{' in wc for wc in benchmark_wildcards):
           #         updated_rule_text = rule_text + formatted_benchmark_section
           #     else:
           #         updated_rule_text = rule_text + benchmark_section
           #     new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
           #     print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeat")
           # elif benchmark_count is not None:
           #     if any('{{' in wc for wc in benchmark_wildcards):
           #         updated_rule_text = rule_text + repeat_formatted_benchmark_section
           #     else:
           #         updated_rule_text = rule_text + repeat_benchmark_section
           #     new_rule_data[rule_name] = {'benchmarks': updated_rule_text}
           #     print(f"\nAdded benchmark section to rule '{rule_name}' with {benchmark_count} repeats")
            #add rulname max s rss
            if resources is True:
                print(f"Adding the resources {max_rss_max} mem_mb and {s_max} runtime to '{rule_name}'")
                updated_rule_text = rule_text + resources_section
                print(updated_rule_text)
                new_rule_data[rule_name] = {'resources': updated_rule_text}
                print(new_rule_data,)
            elif verbose:
                print(f"\nNo resources section to remove from rule '{rule_name}'")
        #new_rule_data[rule_name].update({'resources': rule_text})

    # Rule doesn't match the target_rule_pattern and therefore must be a pseudo-ruledding and removing benchmark section
    else:
        top_level_rules.append(rule_name)


#https://stackoverflow.com/questions/14117415/how-can-i-constrain-a-value-parsed-with-argparse-for-example-restrict-an-integ
def check_positive(value):
    try:
        int_value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("\n%s is not an integer" % value)

    if int_value <= 0:
        raise argparse.ArgumentTypeError("\n%s is not a positive integer" % value)
    return int_value


def calculate_values(fp):
    df = pd.read_csv(fp, sep="\t")
    df = df.drop(columns=["h:m:s"])

    rules = df.copy()
    rules['filename'] = df['filename'].str.split('.').str[0]

    agg_columns = ["s", "max_rss", "cpu_time"] # The column options are ["s", "max_rss", "max_vms", "max_uss", "max_pss", "mean_load", "cpu_time"]
    agg_functions = ["mean", "max", "min"]

    grouped = df.groupby("filename")[agg_columns].agg(agg_functions).round(0)
    concise = rules.groupby("filename")[agg_columns].agg(agg_functions).round(0)

    grouped.columns = [f"{col}_{agg}" for col in grouped.columns.levels[0] for agg in grouped.columns.levels[1]]
    concise.columns = [f"{col}_{agg}" for col in concise.columns.levels[0] for agg in concise.columns.levels[1]]


    return grouped, concise

def combine_tsvs(input_dir, output):
    # ls_filenames = [ x for x in glob('*.{}'.format('tsv')) ] #This gives a list of all files in working dir
    # os.walk was easier but could try fn
    for root, dirs, files in os.walk(f'{input_dir}'):
        list_filenames= [ str.rsplit(file, sep='.', maxsplit=1)[0] for file in files]

    dataframes = []

    for fp in sorted(list_filenames):
        df = pd.read_csv(input_dir + "/" + fp + ".tsv", sep='\t')
        df['filename'] = fp
        dataframes.append(df)

    combined_tsv = pd.concat(dataframes)
    combined_tsv.to_csv(output, sep='\t', index=False)


if __name__ == "__main__":
    main()
                                     