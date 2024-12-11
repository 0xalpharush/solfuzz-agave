import argparse
from tomlkit import parse, inline_table, table
import re
import os
import subprocess

def replace_path_with_git_rev(toml_data, git_url, rev):
    """
    Recursively process the TOML data to replace path with git and rev,
    while keeping all other lines intact.
    """
    if isinstance(toml_data, dict):
        for key, value in list(toml_data.items()):
            if isinstance(value, dict):
                if "path" in value:
                    # Replace path with git and rev
                    new_table = inline_table()
                    new_table["git"] = git_url
                    new_table["rev"] = rev
                    toml_data[key] = new_table
                else:
                    replace_path_with_git_rev(value, git_url, rev)
            elif isinstance(value, list):
                for item in value:
                    replace_path_with_git_rev(item, git_url, rev)
    elif isinstance(toml_data, list):
        for item in toml_data:
            replace_path_with_git_rev(item, git_url, rev)

def replace_path_with_local(toml_data, local_path):
    """
    Recursively process the TOML data to replace path with git and rev,
    while keeping all other lines intact.
    """
    if isinstance(toml_data, dict):
        for key, value in list(toml_data.items()):
            if isinstance(value, dict):
                if "path" in value:
                    # Replace path with local path
                    new_table = inline_table()
                    new_table["path"] = local_path + "/" + value["path"]
                    toml_data[key] = new_table
                else:
                    replace_path_with_local(value, local_path)
            elif isinstance(value, list):
                for item in value:
                    replace_path_with_local(item, local_path)
    elif isinstance(toml_data, list):
        for item in toml_data:
            replace_path_with_local(item, local_path)

def flatten_workspace(toml_data):
    """
    Move keys from "workspace." level to the top level and remove specific keys.
    """
    if "workspace" in toml_data:
        workspace_data = toml_data.pop("workspace")
        # Remove members, exclude, resolver keys
        workspace_data.pop("members", None)
        workspace_data.pop("exclude", None)
        workspace_data.pop("resolver", None)
        for key, value in workspace_data.items():
            if key not in toml_data:
                toml_data[key] = value

def parse_toml_file(file_path):
    """
    Read the TOML file and return the parsed data.
    """
    with open(file_path, "r") as f:
        return parse(f.read())

def main():

    parser = argparse.ArgumentParser(description="Process input files.")
    
    # # Add flags
    parser.add_argument("--commit", "-c", help="Commit in firedancer-io/agave to use")
    parser.add_argument("--agave-path", "-p", help="Commit in firedancer-io/agave to use")
    parser.add_argument("--output", "-o", help="Path to the output file")

    args = parser.parse_args()

    if args.agave_path:
        toml_data = parse_toml_file(args.agave_path + "/Cargo.toml")
        flatten_workspace(toml_data)
        replace_path_with_local(toml_data, args.agave_path)
    else:
        url = f"https://raw.githubusercontent.com/firedancer-io/agave/{args.commit}/Cargo.toml"
        os.makedirs("dump", exist_ok=True)
        try:
            subprocess.run(
                ["curl", "-o", os.path.join("dump", "Cargo.toml"), url],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while downloading the file: {e}")

        toml_data = parse_toml_file("dump/Cargo.toml")
        flatten_workspace(toml_data)
        replace_path_with_git_rev(toml_data, "https://github.com/firedancer-io/agave", args.commit)        

    # some clean up
    toml_data["package"] = table()
    for dep_to_remove in ["pickledb", "winreg"]:
        if dep_to_remove in toml_data.get("dependencies", {}):
            del toml_data["dependencies"][dep_to_remove]
    
    # add required solfuzz-agave added configurations
    solfuzz_agave_config = parse_toml_file("solfuzz_agave.toml")
    for section, values in solfuzz_agave_config.items():
        if section not in toml_data:
            toml_data[section] = table()
        elif not isinstance(toml_data[section], dict):
            continue
        for k, v in values.items():
            toml_data[section][k] = v

    # Write the updated data to the output TOML file
    with open(args.output, "w") as f:
        f.write(toml_data.as_string())

if __name__ == "__main__":
    main()
