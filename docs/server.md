]633;E;printf "# Сервер %s\\n\\n> Последнее обновление: %s\\n\\n" "$host" "$now";b848759b-d4a6-47be-85be-640ca0561717]633;C# Сервер localhost

> Последнее обновление: 2025-08-09T00:54:27+03:00

## ОС
Distributor ID:	Ubuntu
Description:	Ubuntu 20.04.6 LTS
Release:	20.04
Codename:	focal

## Ядро
Linux localhost 5.4.0-182-generic #202-Ubuntu SMP Fri Apr 26 12:29:36 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux

## Аппаратное обеспечение
CPU(s):                             2
On-line CPU(s) list:                0,1
Thread(s) per core:                 1
Core(s) per socket:                 1
Model name:                         AMD EPYC Processor
NUMA node0 CPU(s):                  0,1
              total        used        free      shared  buff/cache   available
Mem:          1,9Gi       1,5Gi        81Mi        59Mi       333Mi       187Mi
Swap:         1,0Gi       782Mi       241Mi
NAME     SIZE MOUNTPOINT         FSTYPE   TYPE
loop0    7,2M /snap/ngrok/295    squashfs loop
loop1    323M /snap/code/202     squashfs loop
loop2  104,2M /snap/core/17212   squashfs loop
loop3   63,8M /snap/core20/2599  squashfs loop
loop4   91,9M /snap/lxd/32662    squashfs loop
loop5   66,8M /snap/core24/1055  squashfs loop
loop6   54,9M /snap/certbot/4892 squashfs loop
loop7    7,2M /snap/ngrok/300    squashfs loop
loop9   73,9M /snap/core22/2045  squashfs loop
loop10  49,3M /snap/snapd/24792  squashfs loop
loop13   4,4M /snap/tree/54      squashfs loop
vda       40G                             disk
└─vda1    40G /                  ext4     part
vdb        1M                             disk

## Сеть
1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
2: eth0    inet 147.45.232.192/24 brd 147.45.232.255 scope global eth0\       valid_lft forever preferred_lft forever
2: eth0    inet 185.125.202.151/24 brd 185.125.202.255 scope global eth0\       valid_lft forever preferred_lft forever
2: eth0    inet 147.45.186.53/24 brd 147.45.186.255 scope global eth0\       valid_lft forever preferred_lft forever
3: wg0    inet 10.20.0.1/24 scope global wg0\       valid_lft forever preferred_lft forever
5: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\       valid_lft forever preferred_lft forever
125: br-923c2a0eb3c3    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-923c2a0eb3c3\       valid_lft forever preferred_lft forever

## Открытые порты
Netid State  Recv-Q Send-Q                    Local Address:Port   Peer Address:Port                                                                            Process                                                                         
udp   UNCONN 0      0                         127.0.0.53%lo:53          0.0.0.0:*                                                                                users:(("systemd-resolve",pid=2188,fd=12))                                     
udp   UNCONN 0      0                               0.0.0.0:9443        0.0.0.0:*                                                                                users:(("ocserv-main",pid=726,fd=6))                                           
udp   UNCONN 0      0                               0.0.0.0:8443        0.0.0.0:*                                                                                                                                                               
udp   UNCONN 0      0      [fe80::3cd0:53ff:fed7:597b]%eth0:546            [::]:*                                                                                users:(("systemd-network",pid=649,fd=19))                                      
udp   UNCONN 0      0                                  [::]:9443           [::]:*                                                                                users:(("ocserv-main",pid=726,fd=7))                                           
udp   UNCONN 0      0                                  [::]:8443           [::]:*                                                                                                                                                               
tcp   LISTEN 0      1024                          127.0.0.1:38965       0.0.0.0:*                                                                                users:(("cursor-54c27320",pid=1262815,fd=9))                                   
tcp   LISTEN 0      4096                      127.0.0.53%lo:53          0.0.0.0:*                                                                                users:(("systemd-resolve",pid=2188,fd=13))                                     
tcp   LISTEN 0      128                             0.0.0.0:22          0.0.0.0:*                                                                                users:(("sshd",pid=810,fd=3))                                                  
tcp   LISTEN 0      511                           127.0.0.1:38967       0.0.0.0:*                                                                                users:(("node",pid=1261613,fd=29))                                             
tcp   LISTEN 0      1024                          127.0.0.1:45463       0.0.0.0:*                                                                                users:(("cursor-54c27320",pid=1261497,fd=10))                                  
tcp   LISTEN 0      200                             0.0.0.0:5432        0.0.0.0:*                                                                                users:(("postgres",pid=420199,fd=6))                                           
tcp   LISTEN 0      2048                            0.0.0.0:8000        0.0.0.0:*                                                                                users:(("uvicorn",pid=1152921,fd=11))                                          
tcp   LISTEN 0      1024                          127.0.0.1:36641       0.0.0.0:*                                                                                users:(("cursor-54c27320",pid=1120058,fd=10))                                  
tcp   LISTEN 0      128                             0.0.0.0:10050       0.0.0.0:*                                                                                users:(("zabbix_agentd",pid=776,fd=4),("zabbix_agentd",pid=775,fd=4),("zabbix_agentd",pid=774,fd=4),("zabbix_agentd",pid=773,fd=4),("zabbix_agentd",pid=751,fd=4))
tcp   LISTEN 0      1024                            0.0.0.0:9443        0.0.0.0:*                                                                                users:(("ocserv-main",pid=726,fd=3))                                           
tcp   LISTEN 0      70                            127.0.0.1:33060       0.0.0.0:*                                                                                users:(("mysqld",pid=1263230,fd=21))                                           
tcp   LISTEN 0      1024                          127.0.0.1:40293       0.0.0.0:*                                                                                users:(("cursor-54c27320",pid=932697,fd=10))                                   
tcp   LISTEN 0      4096                          127.0.0.1:62789       0.0.0.0:*                                                                                users:(("xray-linux-amd6",pid=904,fd=3))                                       
tcp   LISTEN 0      4096                            0.0.0.0:27017       0.0.0.0:*                                                                                users:(("mongod",pid=722,fd=11))                                               
tcp   LISTEN 0      151                             0.0.0.0:3306        0.0.0.0:*                                                                                users:(("mysqld",pid=1263230,fd=23))                                           
tcp   LISTEN 0      511                           127.0.0.1:6379        0.0.0.0:*                                                                                users:(("redis-server",pid=852,fd=6))                                          
tcp   LISTEN 0      128                                [::]:22             [::]:*                                                                                users:(("sshd",pid=810,fd=4))                                                  
tcp   LISTEN 0      200                                [::]:5432           [::]:*                                                                                users:(("postgres",pid=420199,fd=7))                                           
tcp   LISTEN 0      511                                   *:443               *:*                                                                                users:(("apache2",pid=1257620,fd=6),("apache2",pid=1256059,fd=6),("apache2",pid=1256053,fd=6),("apache2",pid=1251097,fd=6),("apache2",pid=1250575,fd=6),("apache2",pid=1250387,fd=6),("apache2",pid=1250386,fd=6),("apache2",pid=1250385,fd=6),("apache2",pid=1250384,fd=6),("apache2",pid=1250383,fd=6),("apache2",pid=1077483,fd=6))
tcp   LISTEN 0      1024                               [::]:9443           [::]:*                                                                                users:(("ocserv-main",pid=726,fd=5))                                           
tcp   LISTEN 0      4096                                  *:2053              *:*                                                                                users:(("x-ui",pid=750,fd=3))                                                  
tcp   LISTEN 0      511                                   *:80                *:*                                                                                users:(("apache2",pid=1257620,fd=4),("apache2",pid=1256059,fd=4),("apache2",pid=1256053,fd=4),("apache2",pid=1251097,fd=4),("apache2",pid=1250575,fd=4),("apache2",pid=1250387,fd=4),("apache2",pid=1250386,fd=4),("apache2",pid=1250385,fd=4),("apache2",pid=1250384,fd=4),("apache2",pid=1250383,fd=4),("apache2",pid=1077483,fd=4))

## ПО и версии
Python 3.12.11
openai              1.74.0
psycopg2-binary     2.9.6
python-telegram-bot 20.4
 nginx/1.18.0 (Ubuntu)
Server version: Apache/2.4.41 (Ubuntu)
Docker version 28.1.1, build 4eba377
Docker Compose version v2.35.1
psql (PostgreSQL) 17.4 (Ubuntu 17.4-1.pgdg20.04+2)

## Активные сервисы
  UNIT                         LOAD   ACTIVE SUB     DESCRIPTION                                 
  accounts-daemon.service      loaded active running Accounts Service                            
  apache2.service              loaded active running The Apache HTTP Server                      
  atd.service                  loaded active running Deferred execution scheduler                
  chatgpt-telegram-bot.service loaded active running ChatGPT Telegram Bot                        
  containerd.service           loaded active running containerd container runtime                
  cron.service                 loaded active running Regular background program processing daemon
  dbus.service                 loaded active running D-Bus System Message Bus                    
  diabetes_bot.service         loaded active running Diabetes Telegram Bot                       
  docker.service               loaded active running Docker Application Container Engine         
  fail2ban.service             loaded active running Fail2Ban Service                            
  getty@tty1.service           loaded active running Getty on tty1                               
  irqbalance.service           loaded active running irqbalance daemon                           
  mongod.service               loaded active running MongoDB Database Server                     
  multipathd.service           loaded active running Device-Mapper Multipath Device Controller   
  mysql.service                loaded active running MySQL Community Server                      
  networkd-dispatcher.service  loaded active running Dispatcher daemon for systemd-networkd      
  ocserv.service               loaded active running OpenConnect SSL VPN server                  
  polkit.service               loaded active running Authorization Manager                       
  postgresql@17-main.service   loaded active running PostgreSQL Cluster 17-main                  
  qemu-guest-agent.service     loaded active running QEMU Guest Agent                            
  redis-server.service         loaded active running Advanced key-value store                    
  rsyslog.service              loaded active running System Logging Service                      
  serial-getty@ttyS0.service   loaded active running Serial Getty on ttyS0                       
  snapd.service                loaded active running Snap Daemon                                 
  ssh.service                  loaded active running OpenBSD Secure Shell server                 
  systemd-journald.service     loaded active running Journal Service                             
  systemd-logind.service       loaded active running Login Service                               
  systemd-networkd.service     loaded active running Network Service                             
  systemd-resolved.service     loaded active running Network Name Resolution                     
  systemd-timesyncd.service    loaded active running Network Time Synchronization                
  systemd-udevd.service        loaded active running udev Kernel Device Manager                  
  udisks2.service              loaded active running Disk Manager                                
  unattended-upgrades.service  loaded active running Unattended Upgrades Shutdown                
  user@0.service               loaded active running User Manager for UID 0                      
  x-ui.service                 loaded active running x-ui Service                                
  zabbix-agent.service         loaded active running Zabbix Agent                                

LOAD   = Reflects whether the unit definition was properly loaded.
ACTIVE = The high-level unit activation state, i.e. generalization of SUB.
SUB    = The low-level unit activation state, values depend on unit type.

36 loaded units listed.

## Брандмауэр
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
5432/tcp                   ALLOW IN    Anywhere                  
27017                      ALLOW IN    Anywhere                  
80,443/tcp (Apache Full)   ALLOW IN    Anywhere                  
5000/tcp                   ALLOW IN    Anywhere                  
22/tcp (OpenSSH)           ALLOW IN    Anywhere                  
5432/tcp (v6)              ALLOW IN    Anywhere (v6)             
27017 (v6)                 ALLOW IN    Anywhere (v6)             
80,443/tcp (Apache Full (v6)) ALLOW IN    Anywhere (v6)             
5000/tcp (v6)              ALLOW IN    Anywhere (v6)             
22/tcp (OpenSSH (v6))      ALLOW IN    Anywhere (v6)             


## Cron & Timers
> Cron jobs should run with Python 3.12. Update the `/usr/bin/python3` symlink or use `/usr/bin/python3.12` directly.
# Edit this file to introduce tasks to be run by cron.
#
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
# 
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').
# 
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
# 
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
# 
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
# 
# For more information see the manual pages of crontab(5) and cron(8)
#
# m h  dom mon dow   command
*/5 * * * * /usr/bin/python3.12 /opt/ddns_updater/update_dns.py >> /opt/ddns_updater/update_dns.log 2>&1
*/5 * * * * wget -q -O - https://blog.offonika.ru/wp-cron.php?doing_wp_cron > /dev/null 2>&1
NEXT                        LEFT           LAST                        PASSED     UNIT                         ACTIVATES
Sat 2025-08-09 01:09:00 MSK 14min left     Sat 2025-08-09 00:39:03 MSK 15min ago  phpsessionclean.timer        phpsessionclean.service       
Sat 2025-08-09 04:39:50 MSK 3h 45min left  Fri 2025-08-08 11:12:22 MSK 13h ago    apt-daily.timer              apt-daily.service             
Sat 2025-08-09 05:26:35 MSK 4h 32min left  Fri 2025-08-08 11:12:23 MSK 13h ago    fwupd-refresh.timer          fwupd-refresh.service         
Sat 2025-08-09 05:47:00 MSK 4h 52min left  Fri 2025-08-08 14:14:03 MSK 10h ago    snap.certbot.renew.timer     snap.certbot.renew.service    
Sat 2025-08-09 06:02:35 MSK 5h 8min left   Fri 2025-08-08 06:55:03 MSK 17h ago    apt-daily-upgrade.timer      apt-daily-upgrade.service     
Sat 2025-08-09 06:40:28 MSK 5h 45min left  Fri 2025-08-08 16:13:51 MSK 8h ago     motd-news.timer              motd-news.service             
Sat 2025-08-09 07:14:07 MSK 6h left        Fri 2025-08-08 07:14:07 MSK 17h ago    systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service
Sun 2025-08-10 00:00:00 MSK 23h left       Sat 2025-08-09 00:00:03 MSK 54min ago  logrotate.timer              logrotate.service             
Sun 2025-08-10 00:00:00 MSK 23h left       Sat 2025-08-09 00:00:03 MSK 54min ago  man-db.timer                 man-db.service                
Sun 2025-08-10 03:10:09 MSK 1 day 2h left  Sun 2025-08-03 03:10:57 MSK 5 days ago e2scrub_all.timer            e2scrub_all.service           
Mon 2025-08-11 00:00:00 MSK 1 day 23h left Mon 2025-08-04 00:00:01 MSK 5 days ago fstrim.timer                 fstrim.service                
n/a                         n/a            Fri 2025-08-08 11:12:23 MSK 13h ago    certbot.timer                                              
n/a                         n/a            n/a                         n/a        snapd.snap-repair.timer      snapd.snap-repair.service     
n/a                         n/a            n/a                         n/a        ua-timer.timer               ua-timer.service              

14 timers listed.
