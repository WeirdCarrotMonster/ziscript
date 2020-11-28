# ziscript

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Pure python 3.6+, no packages required

Usage example

1. Obtain dump files from https://github.com/zapret-info/z-i
2. Extract IPs from dump files

```
./dump_to_ips.py dump*.csv -o /tmp/blocked.txt
```

3. Group IPs into subnets

```
./ips_to_subnets.py -i /tmp/blocked.txt --filter-special -p 0.2 -o /tmp/blocked_subnets.txt
```

4. (Optional) Save your existing ipset into file

```
sudo ipset save rkn-blocked-subnets -output plain > /tmp/old_subnets.txt
```

5. Generate diff between current state and new subnets

```
./ipset_build_delta.py rkn-blocked-subnets --new=/tmp/blocked_subnets.txt --old=/tmp/old_subnets.txt -o /tmp/subnet_delta.txt
```

6. Apply changes to ipset

```
cat /tmp/subnet_delta.txt | sudo ipset restore
```

7. Wrap it in script, add to cron, enjoy using internet
