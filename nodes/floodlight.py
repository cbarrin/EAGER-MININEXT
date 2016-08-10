import shutil
import subprocess
from os import chdir
from os import makedirs
from os import path

import jprops
from mininet.moduledeps import pathCheck
from mininet.node import Controller
from mininext.cli import CLI
from mininext.net import MiniNExT as Mininext


class Floodlight(Controller):

    # Port numbers used to run Floodlight. These must be unique for every instance.
    # Static class variables are used to keep track of which ports have been used already.
    sync_manager_port = 6009
    openflow_port = 6653
    http_port = 8080
    https_port = 8081

    # Number of Floodlight instances created. Used for naming purposes.
    controller_number = 0

    # The Floodlight folder.
    fl_root_dir = subprocess.check_output('git rev-parse --show-toplevel', shell=True).strip() + '/floodlight/'

    def __init__(self, name,
                 command='java -jar ' + fl_root_dir + 'target/floodlight.jar',
                 cargs='',
                 ip='127.0.0.1',
                 **kwargs):

        # Check to make sure Floodlight is installed before moving forward.
        installFloodlight()

        # Increment the number of controller instances for naming purposes.
        Floodlight.controller_number += 1

        # Initialize attributes
        self.properties_path = ''
        self.properties_file = ''

        self.createUniqueFloodlightPropertiesFile()

        # Create the command that will start Floodlight, including the path to the unique properties file.
        self.command = command + ' -cf ' + self.properties_path + self.properties_file

        # Initialize the parent class.
        Controller.__init__(self, name, cdir=self.fl_root_dir,
                            command=self.command,
                            cargs=cargs, ip=ip, **kwargs)

    def start(self):
        """Start <controller> <args> on controller.
           Log to /tmp/cN.log"""
        print('Starting controller')
        pathCheck(self.command)
        cout = '/tmp/' + self.name + '.log'
        chdir(self.fl_root_dir)
        self.cmd(self.command + ' ' + self.cargs +
                 ' 1>' + cout + ' 2>' + cout + '&')
        self.execed = False

    def createUniqueFloodlightPropertiesFile(self):
        """
        Creates a unique properties file for the particular Floodlight instance.
        Each file is put in the 'properties' folder in the floodlight directory.
        Static class attributes keep track of the current port number to use.
        :return: None
        """

        # The path to the properties file to be copied and the name of the file
        old_path = Floodlight.fl_root_dir + 'src/main/resources/'
        old_file = 'floodlightdefault.properties'

        # The path where the new properties file will be located and the name of the file
        new_path = Floodlight.fl_root_dir + 'properties/'
        new_file = 'floodlight' + str(Floodlight.controller_number) + '.properties'

        # Set the instance attributes so that the instance can know where its associated properties file is
        self.properties_path = new_path
        self.properties_file = new_file

        # Check if the new path already exists. If not, then create it
        if not path.exists(new_path):
            makedirs(new_path)

        # Copy the old properties file to the new location with the new name
        shutil.copy(old_path + old_file,
                    new_path + new_file)

        # Open the new properties file and scan it for the ports that need to be changed
        with open(new_path + new_file) as fp:
            properties = jprops.load_properties(fp)

            properties[[key for key, value in properties.items() if key.endswith('httpPort')][0]] = str(
                Floodlight.http_port + 10)
            properties[[key for key, value in properties.items() if key.endswith('httpsPort')][0]] = str(
                Floodlight.https_port + 10)
            properties[[key for key, value in properties.items() if key.endswith('openFlowPort')][0]] = str(
                Floodlight.openflow_port + 10)
            properties[[key for key, value in properties.items() if key.endswith('SyncManager.port')][0]] = str(
                Floodlight.sync_manager_port + 10)

            # Update the class attributes so that everyone knows what ports are available now
            Floodlight.http_port += 10
            Floodlight.https_port += 10
            Floodlight.openflow_port += 10
            Floodlight.sync_manager_port += 10

            # print [value for key, value in properties.items() if key.endswith('httpPort')][0]
            # print [value for key, value in properties.items() if key.endswith('httpsPort')][0]
            # print [value for key, value in properties.items() if key.endswith('openFlowPort')][0]
            # print [value for key, value in properties.items() if key.endswith('SyncManager.port')][0]

        # Write the updated ports to the new properties file
        with open(new_path + new_file, 'w') as fp:
            # print 'Writing to file ' + new_file
            jprops.store_properties(fp, properties)


def isFloodlightInstalled():
    """
    This is a helper function to determine whether floodlight has been installed.
    :return: true or false
    """
    if not path.isdir('../floodlight'):
        # print('Floodlight is not installed.')
        return False
    else:
        # print('Floodlight has been installed.')
        return True


def installFloodlight():
    """
    Installs floodlight in the root folder of the git project.
    :return: none
    """
    if not isFloodlightInstalled():
        print('Installing Floodlight...')
        git_root_dir = subprocess.check_output('git rev-parse --show-toplevel', shell=True)
        git_root_dir = git_root_dir.strip()
        subprocess.call('git clone http://github.com/floodlight/floodlight ' + git_root_dir + '/floodlight', shell=True)
        chdir(git_root_dir + '/floodlight')
        subprocess.call('sudo ant', shell=True)
        chdir(git_root_dir)


print('Testing...')

net = Mininext(topo=None, build=False)

for x in range(0, 20):
    net.addController(name='c' + str(x), controller=Floodlight)

net.build()

for controller in net.controllers:
    controller.start()

CLI(net)
net.stop()
