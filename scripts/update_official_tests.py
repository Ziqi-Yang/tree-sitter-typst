#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
import pathlib

CORPUS_OFFICIAL_DIR_NAME = "official"

def run_shell_command(command, working_directory, exit_on_error = True) -> str | None:
    """
    Helper function to execute a shell command with error checking.
    """
    try:
        result = subprocess.run(
            command, cwd=working_directory, check=exit_on_error, capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        sys.exit(f"Command '{command}' failed: {e.stderr.strip()}")


def check_typst_repo_update(typst_repo, commit_id):
    """
    Function to handle git operations within typst_repo
    """
    print("Checking typst_repo updates...")
    
    run_shell_command(["git", "pull"], typst_repo)

    # Get the current commit ID
    current_commit = run_shell_command(["git", "rev-parse", "HEAD"], typst_repo)

    if commit_id is None:
        return current_commit

    if current_commit != commit_id:
        diff_output = run_shell_command(
            ["git", "diff", commit_id, "HEAD", "./tests/typ/"], typst_repo
        )
        diff_name_only_output = run_shell_command(
            ["git", "diff", "--name-only", commit_id, "HEAD"], typst_repo
        )

        # Save user's current directory for file writing
        user_current_directory = os.getcwd()

        test_changes_filename = "TEST_CHANGES"
        test_changes_name_only = "TEST_CHANGES_NAME_ONLY"
        with open(os.path.join(user_current_directory, test_changes_filename), "w") as file:
            file.write(diff_output)

        with open(
            os.path.join(user_current_directory, test_changes_name_only), "w"
        ) as file:
            file.write(diff_name_only_output)

        print(f"Diff saved to file {test_changes_filename} and {test_changes_name_only}.\nPlease also manually update the COMMIT file.")
        sys.exit(0)
    else:
        sys.exit("The current state is the newest. No update is needed.")


def is_test_block_empty(test_block) -> bool:
    # Determine if a test block contains only comments or is empty
    lines = test_block.strip().splitlines()
    non_comment_lines = [line for line in lines if not line.strip().startswith("//")]
    return not non_comment_lines


def convert_test_block(parse_repo_dir, corpus_dir, test_block, test_number, output_dir):
    # Write the content of the test block to the corresponding .scm file
    scm_filename = f"test{test_number}.scm"
    scm_filepath = os.path.join(output_dir, scm_filename)
    output_dir_relative_path = os.path.join(CORPUS_OFFICIAL_DIR_NAME, os.path.relpath(output_dir, corpus_dir))
    with open(scm_filepath, "w") as scm_file:
        scm_file.write(test_block)

    header = f"==================\n{output_dir_relative_path} Test {test_number}\n==================\n\n"
    with open(scm_filepath, "w") as scm_file:
        scm_file.write(f"{header}{test_block}\n---\n")
    print(f"Converted: {scm_filepath}")

def parse_typ_files_and_convert(tests_dir, corpus_dir, parse_repo_dir):
    # Traverse tests/typ directory and convert .typ files into .scm files
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".typ"):
                filepath = os.path.join(root, file)
                with open(filepath, "r") as f:
                    content = f.read()

                # a test starts with '---' or beginning of file
                test_blocks = content.split("---")
                output_dir = os.path.join(corpus_dir + root[len(tests_dir) :], pathlib.Path(file).stem)
                os.makedirs(output_dir, exist_ok=True)

                for i, test_block in enumerate(test_blocks):
                    if not is_test_block_empty(test_block):
                        convert_test_block(
                            parse_repo_dir, corpus_dir, test_block, i, output_dir
                        )
                        
    # update tests using current parser test output
    # run_shell_command(["tree-sitter", "test", "-u"], parser_repo_path) # this will affect other tests

def yn_question(question: str) -> bool:
    user_input = ""

    while True:
        user_input = input(f"{question} [y/n]:")

        if user_input.upper() == "Y":
            return True
        elif user_input.lower() == "N":
            return False
        else:
            print("Enter Y or N")
            continue


def main(typst_repo, parser_repo):
    # Check if the directories exist
    for path in (typst_repo, parser_repo):
        if not os.path.isdir(path):
            sys.exit(f"Error: {path} is not a directory or does not exist.")

    commit_id = None
    corpus_official_path = os.path.join(parser_repo, "corpus", CORPUS_OFFICIAL_DIR_NAME)
    if not os.path.exists(corpus_official_path):
        print(f"Detect that there is no directory {corpus_official_path}.")
        answer = yn_question("Do you want to initialize the tests?")
        if answer is False:
            exit(0)
        else:
            os.makedirs(corpus_official_path, exist_ok=True)
    else:
        commit_file_path = os.path.join(corpus_official_path, "COMMIT")
        try:
            with open(commit_file_path, "r") as commit_file:
                commit_id = commit_file.read().strip()
        except FileNotFoundError:
            print(f"Detect that there is no COMMIT file under {corpus_official_path}.")
            answer = yn_question(
                f"Do you want to initialize/reinitialize the tests?\nWARNING: this is dangerous operation, it will delete all the files in {corpus_official_path}.\n"
            )
            if answer is False:
                exit(0)
            else:
                shutil.rmtree(corpus_official_path)
                os.makedirs(corpus_official_path)
                
    # if commit_id is still None, then we need to do initialization
    commit_id = check_typst_repo_update(typst_repo, commit_id)
    # after the above above, only the option 'initialize' exists

    tests_dir = os.path.join(typst_repo, "tests", "typ")
    parse_typ_files_and_convert(tests_dir, corpus_official_path, parser_repo)

    # Write the current commit ID to the COMMIT file
    with open(commit_file_path, "w") as commit_file:
        commit_file.write(commit_id)

    print("All tasks have been completed successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python script.py <typst_repo> <parser_repo>")

    typst_repo_path = sys.argv[1]
    parser_repo_path = sys.argv[2]

    main(typst_repo_path, parser_repo_path)
