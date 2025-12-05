# Solana gossip ip checker
wrote this script to check where solana nodes are runing from. basically it connects to the mainnet gossip protocol via rpc and pulls a list of active nodes.

it doesnt check every single node cus that takes too long, so it grabs a random sample of like 100-150 nodes each time it runs to keep it statistcally relevant.

# what it does
1. queries getClusterNodes on solana mainnet
2. maps the IPs to countries using a free geo api
3. checks if the IP is from a OFAC sanctioned country (iran, north korea, russia, syria, etc)
4. calculates a "non compliance" percentage based on the total nodes we fetched

saves everything to a csv file so u can track it over time

# how to run it
you just need python installed.

install the requests lib:
pip install requests

then run the script:
python gossip_check.py

# output
it generates two files:

1. daily_node_scan.csv: appends the raw data (ip, country, pubkey) here every time it runs. keeps a history.

2. daily_summary.txt: this one just overwrites every day with a quick summary of how many nodes were US vs EU vs Russia etc and the compliance %.

# github actions
I included a workflow file in .github/workflows. if u upload this to github it will run automatically at midnight utc every day.

make sure you go to settings -> actions -> general and enable "Read and write permissions" otherwise the bot cant save the csv file back to the repo.

sometimes the ip geolocation api times out if u run it too fast but the script handles it mostly.

## ofac countries list
right now i have it checking these codes: IR, KP (north korea), CU, SY, RU, BY, VE, MM. you can add more in the python file if u want.
