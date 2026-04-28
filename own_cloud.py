import owncloud

def putfile(src,target):
    oc = owncloud.Client('http://192.168.56.101')
    oc.login('user', 'user')
    #oc.mkdir('testdir')
    oc.put_file(target, src)

def getfile(src, target):
    #oc = owncloud.Client('http://192.168.1.13/owncloud')
    #oc.login('administrator', 'kitesnet')
    oc = owncloud.Client('http://192.168.56.101')
    oc.login('user', 'user')
    oc.get_file(src, target)

import os
def del_local_file(file_path):
    myfile=file_path#"/tmp/foo.txt"
    ## If file exists, delete it ##
    if os.path.isfile(myfile):
        os.remove(myfile)
    else:    ## Show an error ##
        print("Error: %s file not found" % myfile)