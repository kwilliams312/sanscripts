#!/usr/bin/perl -w
#
# Manages Netapp snapshots within a VMWare environment
# Requires virtual machines use RDMs
# this script requires ONTAPI to function
# The basic idea of the program is to list out all the Virtual Machines that are in a particular 
# VMWare DataCenter Cluster. For each of the Virtual Machines found the Network Appliance Filer 
# is checked for a volume with the same name.
#
# Example:	Virual Machine Name: ServerABC 
# 		Netapp Volume Name: vm_ServerABC_cluster1
# 		vmPrefix: vm_
# 		vmPostfix: _cluster1
#
# Todo:
# - rsh/ssh vs ZAPI calls
# - snapmirror management, configuration based snapshots per volume?
# - compiled version
# - document!
################################################################## 

# use strict scope reference
use strict;
# we want lots of warnings
use warnings;

# required Perl modules
use lib 'c:\manage-ontap-sdk-2.0P2\lib\perl\NetApp';
use NaServer;
use Getopt::Long;
use VMware::VIM2Runtime;
use VMware::VILib;
use VMware::VIRuntime;
use IO::File;

# [Script options]
our $naPrefix="vm_"; 				# volume prefix for virtual machine
our $naPostfix=""; 				# volume postfix for virtual machine

our $debug="true"; 				# logging enabled? (true/false)
our $logfile='c:\vmscripts\rdmsnapmgr.log';	# location to store logfile

our $hourly=24; 				# number of hourly snapshots to keep
our $daily=30;					# number of daily snapshots to keep
our $testly=2;					# number of test snapshots to keep

# [VMWare VI configuration]
our $vm_user="vmuser";		# user account with privledges to VI
our $vm_pass="vmpass";			# Password for vm_user
our $vm_Cluster="cluster";		# Virtual Center cluster name	
our $vm_serverUrl='https://someserver/sdk'; #vmware sdk server
our $vm_tmpsnapshotname="q4netapp";

# [Filer configuration]
our $filer="filer"; 				# Filer hostname
our $filer_user="filerusername";				# Filer username
our $filer_pass="filerpass";			# Filer password

# [Snapmirror Filer configuration]
our $sm_filer="smfiler"; 			# Filer hostname
our $sm_filer_user="smfileruser";			# Filer username
our $sm_filer_pass="pass";			# Filer password

# predefined globals for vmware api views. (leave blank)
our $vm_Cluster_view="";
our $host_views ="";
our $vm_views ="";
our $gsnaptype ="";
our $sa =""; # defining the NaServer object used by naConnect


############################################################################################################
# Main Program calls

checkParams($ARGV[0]);
# Create a connection to the VMWare API Server
vmConnect();

# Populate the global view objects with VMWare API views.
# Cluster views, Datacenter view and Virtual Machine views
vmCreateViews();

# Create a connect for the network appliance
naConnect();

# start the snapshot process 
snapshotLoop();

# Disconnect from the VMWare API server 
vmDisconnect();

logPrint("...........Completed Snapshots............");
# End of main Program Calls
############################################################################################################

sub checkParams {
	my $param = shift;
	if ($param eq "daily") {
		$gsnaptype="daily";
	} elsif ($param eq "test") {
		logPrint("Started Script in TEST Mode\n");
		$gsnaptype="test";
		$vm_tmpsnapshotname = "test";
	} else {
		$gsnaptype="hourly";
	}
}
# vmConnect();
# Connect to vmware api server 
###########################################################
sub vmConnect {
#	Util::connect(); ## commented out because we aren't using command line
	Vim::login(service_url => $vm_serverUrl, user_name => $vm_user, password => $vm_pass);
	
}

# vmDisconnect();
# Connect to vmware api server 
###########################################################
sub vmDisconnect {
	Util::disconnect();
}
# vmCreateViews();
# Creates the VMWare api views
###########################################################
sub vmCreateViews {
	# find cluster 
	$vm_Cluster_view = Vim::find_entity_view(view_type => 'ClusterComputeResource',
                                                                 filter => { name => 'Cluster-Prod01' });
	# if we cant find the cluster, error out and die.
	if (!$vm_Cluster_view) {
		die "Cluster '" . $vm_Cluster . "' not found\n";
	}

	#  get all hosts under this cluster 
	$host_views = Vim::find_entity_views(view_type => 'HostSystem',
                                                            begin_entity => $vm_Cluster_view);
	# get all VM's under this cluster 
	if (!defined($ARGV[1])) {
		$vm_views = Vim::find_entity_views(view_type => 'VirtualMachine',
                                                         begin_entity => $vm_Cluster_view);
	} else {
		logPrint("Test Run Started");
		$vm_views = Vim::find_entity_views(view_type => 'VirtualMachine',
							filter => { name => $ARGV[1] });
	}

}
# vmSnapshotRemove(vmname);
# accepts a vm name (config->name).
##########################################################
sub vmSnapshotRemove {
	my $vmname = shift;
	logPrint("Connection Sucessful\n");
	my $vm_view = Vim::find_entity_view (view_type => 'VirtualMachine',
                                              filter => {name => "$vmname"});  # Get the VM of your choice by entering the VM name here
	unless ($vm_view) {
		logPrint("VM $vmname not found.\n");
		return;
	}
	my $ss = $vm_view->snapshot->rootSnapshotList;
	foreach (@$ss) {
		vmDeleteSnapshot($_);
	}
}

# vmsnapshotremove(<ref to snapshot list>)
# accepts a reference to a snapshot list.
##########################################################
sub vmDeleteSnapshot {
	my ($snaps) = @_;
	if ($snaps->name eq $vm_tmpsnapshotname) {  
		logPrint("Deleting the snapshot $vm_tmpsnapshotname\n"); 
		eval {
			Vim::get_view(mo_ref => $snaps->snapshot)->RemoveSnapshot (removeChildren => 0 ); 
		};
		if ($@) {
			logPrint(0, "Error while removing the snapshot Fault: " . $@ . ""   );
		}
	}
	if (defined $snaps->childSnapshotList) {
		my $child = $snaps->childSnapshotList;
		foreach (@$child) {
			vmDeleteSnapshot($_);
		}
	}
}

# snapshotLoop(); 
# Begins the snapshot cycle on all Virtual Machines.
# TODO: add snapmirror commands here as well.
################################################################
sub snapshotLoop {
	foreach (@$vm_views) {
		my $vm_name = $_->name;

		# check for "-nosnap" in the vm name if it exists, skip.
		my $nosnap = substr($vm_name, -7);
		if ($nosnap ne "-nosnap") {
			logPrint( "taking vmware snapshot: " . $vm_name . "\n");

			vmSnapshotCreate($vm_name);

			my $prefixvmname = "$naPrefix$vm_name";
			my $result = naVolumeExists($sa, $prefixvmname);
			logPrint( "** $sa $naPrefix$vm_name\n"); #debug
			if ($result eq "true") {
				naRotateSnapshots($sa, $gsnaptype, $prefixvmname);
				logPrint( "global snaptype = $gsnaptype\n");
				naSnapshotCreate($sa, $vm_name, $gsnaptype);
				logPrint( "taking netapp snapshot\n"); #debug
			}
			vmSnapshotRemove($vm_name);
		}#end if
	}#end for
}#end sub

# naConnect();
# start up the filer connector
###############################################################
sub naConnect {
	$sa = NaServer->new($filer, 1, 1);
	$sa->set_admin_user($filer_user, $filer_pass);
}

# vmSnapshotCreate();
# Start a vmware snapshot using the VI api
###############################################################
sub vmSnapshotCreate {

	my $vmname = shift;

	# get VirtualMachine views for all powered on VM's
        my $vm_views = Vim::find_entity_views(view_type => 'VirtualMachine', filter => {'config.name' => $vmname});

	# snapshot each VM
	foreach (@$vm_views) {
		$_->CreateSnapshot(name => "$vm_tmpsnapshotname",
        	                 description => 'snapshot for netapp quiesce',
	                         memory => 0,
        	                 quiesce => 1);
		logPrint( "Snapshot complete for VM: " . $_->name . "\n");
	}
}

# naSnapshotCreate(<naserverobject>, <volumename>, <snaptype>);
# accepts Netapp server object, virtual machine name, snapshottype
# takes a netapp snapshot on the volume based on the virtual machine name
###############################################################
sub naSnapshotCreate {
	
	my $sa = $_[0];
	my $name = $_[1]; 
	my $snaptype = $_[2];

	my $volname = $naPrefix . $name . $naPostfix;

	logPrint( "vol: $volname \n"); #debug
	my $snapname = $volname . "." . $snaptype . ".1";

	my $output = $sa->invoke("snapshot-create",
				"volume",  $volname,
				"snapshot", $snapname);

	if ($output->results_errno != 0) {
		my $r = $output->results_reason();
		logPrint( "snapshot-create failed: $r\n");
	}
}

#
# naVolumeExists(<naserver object>, <volumename>);
# verifies that volume name exists on netapp device.
# returns true/false string
###############################################################
sub naVolumeExists {
	my $s = $_[0];
	my $volume = $_[1];
	my $result = "false";

	my $output = $sa->invoke("volume-list-info",
				"volume", $volume);

	logPrint( "checking to see if: $volume exists \n"); #debug
	if ($output->results_status() eq "failed"){
		logPrint($output->results_reason() ."\n");
		$result = "false";
		return $result;
	}
	my $volume_info = $output->child_get("volumes");
	my @result = $volume_info->children_get();

	foreach my $vol (@result){
		my $vol_name = $vol->child_get_string("name");
		logPrint(  "netapp found: Volume name: $vol_name I asked for $volume \n");#debug
		if ($vol_name eq $volume) {
			$result = "true";
		} else {
			$result = "false";
		}
	}
	return $result	
}

#
# naRotateSnapshots(<naserver object>, <hourly|daily>, <volume>);
# accepts a server obect reference and either hourly or daily.
# $our hourly is 24, $our daily 
###############################################################
sub naRotateSnapshots{
		
 	my $s = $_[0];
	my $snaptype=$_[1];
	my $volume=$_[2];
	my $snapshot = "";
	my $count = 0;
	logPrint( "snaptype: $snaptype\n"); #debug
	
	# determine the type of snapshot (daily/hourly).
	if ($snaptype eq "hourly"){ 
		$snapshot = "$volume.$snaptype.$hourly";
		$count = $hourly-1;
	} elsif ($snaptype eq "daily") {
		$snapshot = "$volume.$snaptype.$daily";
		$count = $daily-1;
	} elsif ($snaptype eq "test") {
		$snapshot = "$volume.$snaptype.1";
		$count = $testly -1;
	} else {
		Fail("Error: Configuration issue");
	}
	
	# execute the snapshot delete using the string just built $snapshot.
	logPrint( "deleting snapshot: $snapshot on volume: $volume");
	my $result = $s->invoke("snapshot-delete", "snapshot", $snapshot,"volume","$volume");
	if ($result->results_errno != 0) {
		my $r = $result->results_reason();
		logPrint( "snapshot-delete failed: $r\n");
	}
 	
	# rotate 	
	while ($count > 0) {
		my $current_name = "$volume.$snaptype.$count";
		my $nextcount = $count + 1;
		my $new_name = "$volume.$snaptype.$nextcount";

		logPrint( "renaming snapshot from $current_name to $new_name \n"); #debug
		
		# rename the string built previously $current_name to the other string we just built $new_name.
		my $result = $s->invoke("snapshot-rename", "current-name", $current_name, "new-name", $new_name, "volume",$volume);

		# report errors
		if ($result->results_errno != 0) {
			my $r = $result->results_reason();
			logPrint( "snapshot-rename failed: $r\n");
		}
		$count--;
	}
}
sub runExit {
    my ($msg) = @_;
    Util::disconnect();
    die ($msg);
    exit ();
} 

# logPrint
# quick and dirty logging facility
# all parameters are output as a message.
# if $logfile is blank output to stdout.
####################################################
sub logPrint {
	if ($debug eq "true") {
		my $now = localtime time;
		open (FILEHANDLE, ">>$logfile");
			my ($msg) = @_;
			print FILEHANDLE "[$now]: $msg";
			print "[$now]: $msg";
		close (FILEHANDLE);
	}
}
