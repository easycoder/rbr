import functions

###################################################################################
# Get my config data and select the operating mode
myname,hostssid,hostpass,mypass,myip = functions.getConfigData()
if myname==None or hostssid==None or hostpass==None or mypass==None:
    import unconfigured
    unconfigured.run()
else:
    import configured
    configured.run()
