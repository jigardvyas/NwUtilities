#!/bin/bash
echo "Hello World"
echo $SHELL

#run_oir_cycle() {
#    n=10
#    # Enable OIR first
#    cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd oir_enable"
#    # Loop n times
#    for (( i = 0; i < n; i++ )); do
#        echo "Cycle $((i+1)) of $n"
#        cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd remove"
#        cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd insert"
#    done
#    sleep 180
#}
#
#OP_CLI=$(cli -c "show interfaces terse et-0/0/12" | awk 'NR==2 {print $3}')
#echo "et-0/0/12 Interface status is -- $OP_CLI"
#
## Condition Check
#if [ "$OP_CLI" = "up" ]; then
#  echo "Port is UP, Need to run run_oir_cycle() function again"
#  run_oir_cycle
#else
#  cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd oir_disable"
#  echo "et-0/0/12 interface is down - stopping Loop and OIR disabled"
#fi



#############################################

#!/bin/sh

PORT="et-0/0/12"
LOG_FILE="/var/log/oir_cycle.log"

# Redirect all output to log file (and console)
exec > >(tee -a "$LOG_FILE") 2>&1

echo "======================================"
echo "OIR Script Started at $(date)"
echo "Port: $PORT"
echo "======================================"

run_oir_cycle() {
    n=10
    i=0

    echo "$(date): Enabling OIR"
    cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd oir_enable"

    while [ "$i" -lt "$n" ]; do
        i=$((i + 1))
        echo "$(date): OIR Cycle $i of $n"
        cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd remove"
        cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd insert"
    done
}

while : ; do
    # Step 1: Run OIR cycle
    run_oir_cycle

    # Step 2: Wait 180 seconds
    echo "$(date): Waiting 180 seconds before checking port status"
    sleep 180

    # Step 3: Check port status
    OP_CLI=$(cli -c "show interfaces terse $PORT" | awk 'NR==2 {print $3}')
    echo "$(date): $PORT status is $OP_CLI"

    if [ "$OP_CLI" = "up" ]; then
        echo "$(date): Port is UP — continuing OIR cycles"
        continue
    else
        echo "$(date): Port is DOWN — disabling OIR and exiting"
        cprod -A fpc0 -c "test picd optics fpc_slot 0 pic_slot 0 port 12 cmd oir_disable"
        echo "$(date): Script exiting"
        exit 0
    fi
done
