    Create VMs and network:

        achim create-instance --name box1 --keyname t15 --context demo --owner patrick.bucher --group dorks --autostart --image 'Linux Debian 13 (Trixie) 64-bit' --size micro
        achim create-instance --name box2 --keyname t15 --context demo --owner patrick.bucher --group dorks --autostart --image 'Linux Debian 13 (Trixie) 64-bit' --size micro
        achim create-network --name skynet --start-ip 10.0.0.1 --end-ip 10.0.0.100 --netmask 255.255.255.0
    
    Attach VMs to network:

        achim attach-network --instance box1 --network skynet --ip 10.0.0.5
        achim attach-network --instance box2 --network skynet --ip 10.0.0.6
    
    On boxes:

        debian@box1$ sudo ip addr add 10.0.0.5/24 dev eth1
        debian@box2$ sudo ip addr add 10.0.0.6/24 dev eth1

        debian@box1$ sudo ip link set up eth1
        debian@box2$ sudo ip link set up eth1

        debian@box1$ ping 10.0.0.5
        debian@box2$ ping 10.0.0.6
