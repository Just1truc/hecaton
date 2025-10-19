import argparse

parser = argparse.ArgumentParser(
    prog="Hecaton Client",
    description="A simple cli to use the Hecaton Server"
)
# The login is done in CLI
# Saved in .cache/hecaton
# The logout should also be available
# The usage of a server is done in the cli

# CLI
# connect [SERVER]
# new_job, new [filepath] -> job id
# status_job, status [ID] -> (STATUS, results|None)
# get_jobs, get -> Return all running jobs (from the server)
# delete_job, del -> Put a job in failed and free a GPU