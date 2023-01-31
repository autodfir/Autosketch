# Autosketch

Framework to automate forensic workload and upload it to Timesketch 


# 1. Prerequisities 
 - docker-compose
 - Timesketch 

# 2. Deployment
### Automated
```
cd /opt
curl https://raw.githubusercontent.com/autodfir/Autosketch/main/deploy/deploy_as.sh > deploy_as.sh
chmod +x deploy_as.sh
sudo ./deploy_as.sh
```

### Manual
 - copy etc/config.yaml directory to /opt/autosketch/etc
 - copy docker-compose.yaml to /opt/autosketch
 - edit TS_IP and TS_PORT to IP and PORT of Timesketch
 - docker-compose up -d
 

# 3. Access
Access Autosketch by visiting http://127.0.0.1:5001

