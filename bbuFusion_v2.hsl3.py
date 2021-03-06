#encoding=utf-8
# BBU Fusion Script
''' 2021-04-22: Initial release
'''
# ----------------------------------------------------------VARIABLES----------------------------------------------------------#
txModeList = {}
rru2TList = ['MRRU V2', 'RRU3959']
rru1TList = ['MRRU V3', 'RRU3936']
ulArfcn = []
dlArfcn = []
maxPower = []
uLocellRruSrn = {}
# ----------------------------------------------------------FUNCTIONS----------------------------------------------------------#
def cpip_getter(cpbearerf)
    # Function to get DEVIP starting with the CP Bearer ID
    ClearMMLBuffer()
    SendMML('DSP CPBEARER:CPBEARID=' + cpbearerf + ';')
    sctplinkparsed = ParseMMLRpt(GetMMLReport(0))
    # Get SCTP Link ID
    sctplink = GetAttrValueByIdx(sctplinkparsed, 0, 2, 0)
    SendMML('LST SCTPLNK:SCTPNO=' + sctplink + ';')
    devipparsed = ParseMMLRpt(GetMMLReport(0))
    # Get Local IP (DEVIP)
    devipf = GetAttrValueByIdx(devipparsed, 0, 8, 0)
    # Get Peer IP Address
    peeripf = GetAttrValueByIdx(devipparsed, 0, 13, 0)
    return devipf,peeripf
end

def gw_getter(devipf)
    # Function to get Gateway IP starting with the DEVIP
    gwipf = ""
    vlanidf = ""
    ClearMMLBuffer()
    @LST VLANMAP:;
    vlanmapparsed = ParseMMLRpt(GetMMLReport(0))
    gwlist = GetColumnByIndex(vlanmapparsed, 0, 1)
    vlanlist = GetColumnByIndex(vlanmapparsed, 0, 4)
    for i in range(len(gwlist))
        # Check if DEVIP and GW are on the same subnet segment
        if checkip_segment(devipf, gwlist[i])
            gwipf = gwlist[i]
            vlanidf = vlanlist[i]
        end
    end
    return gwipf,vlanidf
end

def checkip_segment(ipf, gwip)
    # Function to determine if an IP and a GW are in the same segment. Arguments are 2 IP address and the function will return True if they are on the same segment, otherwise it'll return False.
    ClearMMLBuffer()
    segment = False
    # Function arguments are tuples. We must convert to string to split by dot.
    iplist = str(ipf).split('.')
    gwiplist = str(gwip).split('.')
    if iplist[0] == gwiplist[0] and iplist[1] == gwiplist[1] and iplist[2] == gwiplist[2]
        segment = True
    end
    return segment
end

def ptp_getter(gwipf)
    # Function to get PTP IP based on the Gateway IP. Will return an IP list.
    ClearMMLBuffer()
    @LST IPCLKLINK:;
    ptpiplst = '0.0.0.0'
    ptplinkparsed = ParseMMLRpt(GetMMLReport(0))
    # Loop through all the reports outputed by the LST command
    for n in range(GetRecordNum(ptplinkparsed, 0))
        ptpip = GetAttrValueByIdx(ptplinkparsed, 0, 9, n)
        # If the IP on the PTP Link is on the same segmente as the Gateway IP, then append it to the ptp ip list.
        if checkip_segment(ptpip, gwipf)
            ptpiplst = ptpip
        else
            continue
        end
    end
    return ptpiplst
end

def om_getter(gwipf)
    # Function to check if OMCH IP is on GW segment. Function takes an IP and checks if the OMCH ip address is on the same segment. If true, it'll return the OMCH IP, otherwise it'll return NULL
    ClearMMLBuffer()
    @LST OMCH:;
    omchlst = '0.0.0.0'
    omchparsed = ParseMMLRpt(GetMMLReport(0))
    # Loop through all the reports outputed by the LST command
    for n in range(GetRecordNum(omchparsed, 0))
        omip = GetAttrValueByIdx(omchparsed, 0, 2, n)
        if checkip_segment(omip, gwipf)
            omchlst = omip
        else
            continue
        end
    end
    return omchlst
end

def upip_getter(devipf)
    ClearMMLBuffer()
    ippathipf = ""
    @LST IPPATH:;
    ippathparsed = ParseMMLRpt(GetMMLReport(0))
    # Get Local IP Column from the LST output
    ippath = GetColumnByIndex(ippathparsed, 0, 17)
    for ip in ippath
        # Check if DEVIP and current local ip on ippath are on the same network segment
        if checkip_segment(devipf, ip)
            ippathipf = ip
            break
        else
            continue
        end
    end
    return ippathipf
end
# -----------------------------------------------------------MAINCODE----------------------------------------------------------#
Print('Altice DR BBU Fusion Tool')
Print('Restrictions: Only works with 3G Configuration, BBP board must be on slot 3, NodeB APP previously configured.\n')
Print('Available Operations:')
Print('1.- BBU Fusion (U->GL = GUL')
Print('2.- L900 Integration (GUL BBU)')
Print('3.- L900 Integration (UO BBU)')
# Ask for user input
option = UserInput('Choose your desired operation: ')
if option == '1'
	srcNe = UserInput('Input 3G NE Name (Ex.: U1122S): ')
	dstNe = UserInput('Input Destination NE Name (Ex.: M1122S): ')
	# First, let's collect the information from the source NE
	ConnectNE(srcNe)
	# Get all local cell IDs
	@LST ULOCELL:MODE=ALLLOCALCELL;
	uLoCellParsed = ParseMMLRpt(GetMMLReport(0))
	uLoCellIdList = GetColumnByName(uLoCellParsed, 0, 'Local Cell ID')
	ClearMMLBuffer()
	# Get Localcell params
	for i in range(len(uLoCellIdList))
		# Get some localcell params
		SendMML('LST ULOCELL:MODE=LOCALCELL,ULOCELLID=' + uLoCellIdList[i] + ';')
		uLocellParamParsed = ParseMMLRpt(GetMMLReport(0))
		ulArfcn.append(GetAttrValueByName(uLocellParamParsed, 0, 'UL Frequency Channel Number', 0))
		dlArfcn.append(GetAttrValueByName(uLocellParamParsed, 0, 'DL Frequency Channel Number', 0))
		maxPower.append(GetAttrValueByName(uLocellParamParsed, 0, 'Max Output Power(0.1dBm)', 0))
		ClearMMLBuffer()
		# Find localcell's sectoreqm to assosiate with RRU srn
		SendMML('LST ULOCELLSECTOREQM:ULOCELLID=' + uLoCellIdList[i] + ';')
		uLocellSectorEqmParsed = ParseMMLRpt(GetMMLReport(0))
		uLocellSectorEqm = GetAttrValueByName(uLocellSectorEqmParsed, 0, 'Sector Equipment ID', 0)
		ClearMMLBuffer()
		SendMML('LST SECTOREQM:SECTOREQMID=' + uLocellSectorEqm + ';')
		sectorEqmPortParsed = ParseMMLRpt(GetMMLReport(0))
		uLocellRruSrn.append(GetAttrValueByName(sectorEqmPortParsed, 1, 'Subrack No.', 0))
		ClearMMLBuffer()
	# for i in range(len(uLoCellIdList))	
	end
	# Get all RRU's TxMode
	@LST RRU:;
	rruSrnParsed = ParseMMLRpt(GetMMLReport(0))
	rruSrnList = GetColumnByName(rruSrnParsed, 0, 'Subrack No.')
	ClearMMLBuffer()
	for srn in rruSrnList
		SendMML('DSP BRDMFRINFO:CN=0,SRN=' + srn + ',SN=0;')
		rruSerialNumParsed = ParseMMLRpt(GetMMLReport(0))
		rruDescription = GetAttrValueByName(rruSerialNumParsed, 0, 'Description', 0)
		ClearMMLBuffer()
		for rruModel in rru2TList
			if rruModel in rruDescription
				txModeList[srn] = '2T2R'
			end
		end
		for rruModel in rru1TList
			if rruModel in rruDescription
				txModeList[srn] = '1T2R'
			end
		end
	# for srn in rruSrnList	
	end
	ClearMMLBuffer()
	# Get IP Information
	# Let's check if there's an IuB Interface Configured.
	@LST IUBCP:;
	iubcpparsedreport = ParseMMLRpt(GetMMLReport(0))
	# Check if there's an IuB interface configured
	if GetRecordNum(iubcpparsedreport, 0) != 0
		iubcpbearer = GetAttrValueByIdx(iubcpparsedreport, 0, 2, 0)
		# Get the CP IP
		umtscpdevip, umtspeerip = cpip_getter(iubcpbearer)
		# Get the gateway for the UMTS IP Segment and the VLAN ID
		umtsgw, umtsvlanid = gw_getter(umtscpdevip)
		# Now we check if the PTP IP is on the UMTS DEVIP Segment
		umtsptpdevip = ptp_getter(umtsgw)
		# Now we check if the O&M IP is on the UMTS DEVIP Segment
		umtsomip = om_getter(umtsgw)
		# Now we look for the UP IP
		umtsupdevip = upip_getter(umtscpdevip)
	else
		Print(StrfTime("%Y%m%d:%H%M%S:") + 'site doesn\'t have NodeB.')
	end
	# Let's configure on the Destination BBU
	ConnectNE(dstNe)
	# Physical Layer
	# Add Baseband Equipment
	SendMML('ADD BRD:SN=3,BT=UBBP,BBWS=GSM-0&UMTS-1&LTE_FDD-0&LTE_TDD-0&NBIOT-0&NR-0,BRDSPEC="UBBPe4";')
	SendMML('ADD BASEBANDEQM:BASEBANDEQMID=0,BASEBANDEQMTYPE=DL,SN1=3;')
	SendMML('ADD BASEBANDEQM:BASEBANDEQMID=0,BASEBANDEQMTYPE=UL,UMTSDEMMODE=DEM_2_CHAN,SN1=3;')
	# Add RRU/Sectors
	for k,v in txModeList.items()
		sector = str(int(k[-1]))
		area = str(int(k[-1])+1)
		SendMML('ADD RRUCHAIN:RCN=8' + area + ',TT=CHAIN,BM=COLD,AT=LOCALPORT,HSRN=0,HSN=3,HPN=' + sector + ',CR=AUTO,USERDEFRATENEGOSW=OFF;')
		if v == '1T2R'
			SendMML('ADD RRU:CN=0,SRN=8' + area + ',SN=0,TP=TRUNK,RCN=8' + area + ',PS=0,RT=MRRU,RS=UL,RN="UL900_' + area + '",RXNUM=2,TXNUM=1,ALMTHRHLD=15,RUSPEC="RRU3936",MNTMODE=NORMAL,RFDCPWROFFALMDETECTSW=OFF,RFTXSIGNDETECTSW=OFF;')
			SendMML('ADD SECTOR:SECTORID=8' + area + ',SECNAME="UL900_' + area + '",ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,CREATESECTOREQM=FALSE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '31,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '32,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '41,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
		else
			SendMML('ADD RRU:CN=0,SRN=8' + area + ',SN=0,TP=TRUNK,RCN=8' + area + ',PS=0,RT=MRRU,RS=UL,RN="UL900_' + area + '",RXNUM=2,TXNUM=2,ALMTHRHLD=15,RUSPEC="RRU3959",MNTMODE=NORMAL,RFDCPWROFFALMDETECTSW=OFF,RFTXSIGNDETECTSW=OFF;')
			SendMML('ADD SECTOR:SECTORID=8' + area + ',SECNAME="UL900_' + area + '",ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,CREATESECTOREQM=FALSE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '31,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '32,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RXTX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '41,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RXTX_MODE;')
		# if v = '1T2R'
		end
	# for k,v in txModeList
	end
	# Configure 3G Cells
	for i in range(len(uLoCellIdList))
		uLocellLastDigit = uLoCellIdList[i][-1]
		if dlArfcn[i] == '3013'
			sectorEqmNum = '1'
			# sectorEqmFace
			sectorEqmFace = str(int(uLocellRruSrn[i]) - 80 + 1)
			# if uLocellLastDigit == '1' or uLocellLastDigit == '4'
			SendMML('ADD ULOCELL:ULOCELLID=' + uLoCellIdList[i] + ',LOCELLTYPE=NORMAL_CELL,SECTOREQMNUM=1,SECTOREQMID1=8' + sectorEqmFace + '3' + sectorEqmNum + ',TTW=FALSE,ULFREQ=' + ulArfcn[i] + ',DLFREQ=' + dlArfcn[i] + ',MAXPWR=' + maxPower[i] + ',DLRESMODE=INEBOARD,HISPM=FALSE,RMTCM=FALSE,VAM=FALSE,DL64QAM=TRUE,DLADAPTIVEBPFILTER=NOTSUPPORT,DLASYMFILTER=FALSE,UL0BUFFERZONE=FALSE,DCHSDPASHAREDWITHGSM=NOTSUPPORT;')
			# Configure Multi-Cell Groups
			SendMML('ADD NODEBMULTICELLGRP:MULTICELLGRPID=' + str(int(sectorEqmFace)-1) + ',MULTICELLGRPTYPE=HSDPA;')
			SendMML('ADD NODEBMULTICELLGRPITEM:MULTICELLGRPID=' + str(int(sectorEqmFace)-1) + ',ULOCELLID=' + uLoCellIdList[i] + ';')
		elif dlArfcn[i] == '3038'
			sectorEqmNum = '2'
			sectorEqmFace = str(int(uLocellRruSrn[i]) - 80 + 1)
			# if uLocellLastDigit == '1' or uLocellLastDigit == '4'
			SendMML('ADD ULOCELL:ULOCELLID=' + uLoCellIdList[i] + ',LOCELLTYPE=NORMAL_CELL,SECTOREQMNUM=1,SECTOREQMID1=8' + sectorEqmFace + '3' + sectorEqmNum + ',TTW=FALSE,ULFREQ=' + ulArfcn[i] + ',DLFREQ=' + dlArfcn[i] + ',MAXPWR=' + maxPower[i] + ',DLRESMODE=INEBOARD,HISPM=FALSE,RMTCM=FALSE,VAM=FALSE,DL64QAM=TRUE,DLADAPTIVEBPFILTER=NOTSUPPORT,DLASYMFILTER=FALSE,UL0BUFFERZONE=FALSE,DCHSDPASHAREDWITHGSM=NOTSUPPORT;')
			SendMML('ADD NODEBMULTICELLGRPITEM:MULTICELLGRPID=' + str(int(sectorEqmFace)-1) + ',ULOCELLID=' + uLoCellIdList[i] + ';')
		# If the current cell is not F1 or F2, skip it and don't configure anything.
		else
			continue
		# if dlArfcn[i] == '3013'
		end
	# for i in range(len(uLoCellIdList))
	end
	# IP Transport Layer
	SendMML('ADD DEVIP:SN=7,SBT=BASE_BOARD,PT=ETH,PN=0,IP="' + umtscpdevip + '",MASK="255.255.255.248",USERLABEL="3G_UP/CP/PTP";')
	SendMML('ADD DEVIP:SN=7,SBT=BASE_BOARD,PT=ETH,PN=0,IP="' + umtsomip + '",MASK="255.255.255.248",USERLABEL="3G_OM";')
	SendMML('ADD VLANMAP:NEXTHOPIP="' + umtsgw + '",MASK="255.255.255.248",VLANMODE=SINGLEVLAN,VLANID=' + umtsvlanid + ',SETPRIO=DISABLE,FORCEEXECUTE=YES;')
	SendMML('ADD IPRT:RTIDX=105,SN=7,SBT=BASE_BOARD,DSTIP="' + umtspeerip + '",DSTMASK="255.255.255.255",RTTYPE=NEXTHOP,NEXTHOP="' + umtsgw + '",MTUSWITCH=OFF,DESCRI="to_RNC",FORCEEXECUTE=YES;')
	#SendMML('ADD IPRT:RTIDX=101,SN=7,SBT=BASE_BOARD,DSTIP="172.16.160.0",DSTMASK="255.255.255.128",RTTYPE=NEXTHOP,NEXTHOP="' + umtsgw + '",MTUSWITCH=OFF,DESCRI="to_U2020_Taishan_Trace_Server_UMTS",FORCEEXECUTE=YES;')
	SendMML('ADD IPRT:RTIDX=103,SN=7,SBT=BASE_BOARD,DSTIP="172.19.8.0",DSTMASK="255.255.255.0",RTTYPE=NEXTHOP,NEXTHOP="' + umtsgw + '",MTUSWITCH=OFF,DESCRI="to_IPCLK3000_UMTS",FORCEEXECUTE=YES;')
	SendMML('ADD IPRT:RTIDX=107,SN=7,SBT=BASE_BOARD,DSTIP="172.17.48.72",DSTMASK="255.255.255.248",RTTYPE=NEXTHOP,NEXTHOP="' + umtsgw + '",MTUSWITCH=OFF,DESCRI="to_NTP_UMTS",FORCEEXECUTE=YES;')
	SendMML('ADD SCTPLNK:SCTPNO=3000,IPVERSION=IPv4,LOCIP="' + umtscpdevip + '",LOCPORT=9000,PEERIP="' + umtspeerip + '",PEERPORT=58080,AUTOSWITCH=ENABLE,DESCRI="NCP";')
	SendMML('ADD SCTPLNK:SCTPNO=3001,IPVERSION=IPv4,LOCIP="' + umtscpdevip + '",LOCPORT=9001,PEERIP="' + umtspeerip + '",PEERPORT=58080,AUTOSWITCH=ENABLE,DESCRI="CCP";')
	SendMML('ADD IPPATH:PATHID=0,TRANSCFGMODE=OLD,SN=7,SBT=BASE_BOARD,PT=ETH,JNRSCGRP=DISABLE,LOCALIP="' + umtscpdevip + '",PEERIP="' + umtspeerip + '",PATHTYPE=FIXED,DSCP=46,IPMUXSWITCH=DISABLE,DESCRI="3G_RT";')
	SendMML('ADD IPPATH:PATHID=1,TRANSCFGMODE=OLD,SN=7,SBT=BASE_BOARD,PT=ETH,JNRSCGRP=DISABLE,LOCALIP="' + umtscpdevip + '",PEERIP="' + umtspeerip + '",PATHTYPE=FIXED,DSCP=10,IPMUXSWITCH=DISABLE,DESCRI="3G_NO_RT";')
	SendMML('ADD IPPATH:PATHID=2,TRANSCFGMODE=OLD,SN=7,SBT=BASE_BOARD,PT=ETH,JNRSCGRP=DISABLE,LOCALIP="' + umtscpdevip + '",PEERIP="' + umtspeerip + '",PATHTYPE=FIXED,DSCP=12,IPMUXSWITCH=DISABLE,DESCRI="3G_DATA";')
	SendMML('ADD CPBEARER:CPBEARID=3000,BEARTYPE=SCTP,LINKNO=3000,FLAG=MASTER;')
	SendMML('ADD CPBEARER:CPBEARID=3001,BEARTYPE=SCTP,LINKNO=3001,FLAG=MASTER;')
	SendMML('ADD IUBCP:CPPT=NCP,CPBEARID=3000;')
	SendMML('ADD IUBCP:CPPT=CCP,CPBEARID=3001;')
elif option == '2'
	currentNe = UserInput('Input NE Name (Ex.: M1122S): ')
	ConnectNE(currentNe)
	# First let's get currentNe information
	# Get all local cell IDs
	@LST ULOCELL:MODE=ALLLOCALCELL;
	uLoCellParsed = ParseMMLRpt(GetMMLReport(0))
	uLoCellIdList = GetColumnByName(uLoCellParsed, 0, 'Local Cell ID')
	ClearMMLBuffer()
	# Get Localcell params
	for i in range(len(uLoCellIdList))
		# Find localcell's sectoreqm to assosiate with RRU srn
		SendMML('LST ULOCELLSECTOREQM:ULOCELLID=' + uLoCellIdList[i] + ';')
		uLocellSectorEqmParsed = ParseMMLRpt(GetMMLReport(0))
		uLocellSectorEqm = GetAttrValueByName(uLocellSectorEqmParsed, 0, 'Sector Equipment ID', 0)
		ClearMMLBuffer()
		SendMML('LST SECTOREQM:SECTOREQMID=' + uLocellSectorEqm + ';')
		sectorEqmPortParsed = ParseMMLRpt(GetMMLReport(0))
		uLocellRruSrn[uLoCellIdList[i]] = GetAttrValueByName(sectorEqmPortParsed, 1, 'Subrack No.', 0)
		ClearMMLBuffer()
		# Get some localcell params
		SendMML('LST ULOCELL:MODE=LOCALCELL,ULOCELLID=' + uLoCellIdList[i] + ';')
		uLocellParamParsed = ParseMMLRpt(GetMMLReport(0))
		ulArfcn.append(GetAttrValueByName(uLocellParamParsed, 0, 'UL Frequency Channel Number', 0))
		dlArfcn.append(GetAttrValueByName(uLocellParamParsed, 0, 'DL Frequency Channel Number', 0))
		maxPower.append(GetAttrValueByName(uLocellParamParsed, 0, 'Max Output Power(0.1dBm)', 0))
		ClearMMLBuffer()
	# for i in range(len(uLoCellIdList))	
	end
	# Get all RRU's TxMode
	@LST RRU:;
	rruSrnParsed = ParseMMLRpt(GetMMLReport(0))
	rruSrnList = GetColumnByName(rruSrnParsed, 0, 'Subrack No.')
	ClearMMLBuffer()
	for srn in rruSrnList
		SendMML('DSP BRDMFRINFO:CN=0,SRN=' + srn + ',SN=0;')
		rruSerialNumParsed = ParseMMLRpt(GetMMLReport(0))
		rruDescription = GetAttrValueByName(rruSerialNumParsed, 0, 'Description', 0)
		ClearMMLBuffer()
		for rruModel in rru2TList
			if rruModel in rruDescription
				txModeList[srn] = '2T2R'
			end
		end
		for rruModel in rru1TList
			if rruModel in rruDescription
				txModeList[srn] = '1T2R'
			end
		end
	# for srn in rruSrnList	
	end
	for k,v in txModeList.items()
		sector = str(int(k[-1]))
		area = str(int(k[-1])+1)
		SendMML('ADD RRUCHAIN:RCN=8' + area + ',TT=CHAIN,BM=COLD,AT=LOCALPORT,HSRN=0,HSN=3,HPN=' + sector + ',CR=AUTO,USERDEFRATENEGOSW=OFF;')
		if v == '1T2R'
			SendMML('ADD RRU:CN=0,SRN=8' + area + ',SN=0,TP=TRUNK,RCN=8' + area + ',PS=0,RT=MRRU,RS=UL,RN="UL900_' + area + '",RXNUM=2,TXNUM=1,ALMTHRHLD=15,RUSPEC="RRU3936",MNTMODE=NORMAL,RFDCPWROFFALMDETECTSW=OFF,RFTXSIGNDETECTSW=OFF;')
			SendMML('ADD SECTOR:SECTORID=8' + area + ',SECNAME="UL900_' + area + '",ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,CREATESECTOREQM=FALSE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '31,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '32,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '41,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
		else
			SendMML('ADD RRU:CN=0,SRN=8' + area + ',SN=0,TP=TRUNK,RCN=8' + area + ',PS=0,RT=MRRU,RS=UL,RN="UL900_' + area + '",RXNUM=2,TXNUM=2,ALMTHRHLD=15,RUSPEC="RRU3959",MNTMODE=NORMAL,RFDCPWROFFALMDETECTSW=OFF,RFTXSIGNDETECTSW=OFF;')
			SendMML('ADD SECTOR:SECTORID=8' + area + ',SECNAME="UL900_' + area + '",ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,CREATESECTOREQM=FALSE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '31,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '32,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RXTX_MODE;')
			SendMML('ADD SECTOREQM:SECTOREQMID=8' + area + '41,SECTORID=8' + area + ',ANTCFGMODE=ANTENNAPORT,ANTNUM=2,ANT1CN=0,ANT1SRN=8' + area + ',ANT1SN=0,ANT1N=R0A,ANTTYPE1=RXTX_MODE,ANT2CN=0,ANT2SRN=8' + area + ',ANT2SN=0,ANT2N=R0B,ANTTYPE2=RXTX_MODE;')
		# if v = '1T2R'
		end
	# for k,v in txModeList
	end
	for k,v in uLocellRruSrn.items()
	#for i in range(len(uLoCellIdList))
		if v == ''
		SendMML('ADD ULOCELLSECTOREQM:ULOCELLID=' + uLoCellIdList[i] + ',SECTOREQMID=8131,SECTOREQMPROPERTY=NORMAL;')
	# for i in range(len(uLoCellIdList))
	end
#elif option == '3'
#	pass
#else
#	Print('Invalid Option....')
# if option == '1'
end
Print('Finished!')