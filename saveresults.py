# -*- coding: utf-8 -*-
#######################################################
# This script saves result data                       #
# It expects the format of unladen swallow's perf.py  #
#######################################################
import urllib, urllib2
from datetime import datetime

SPEEDURL = "http://speed.pypy.org/"

def save(project, revision, results, options, interpreter, host, testing=True,
         changed=True):
    testparams = []
    #Parse data
    data = {}
    error = 0
        
    for b in results:
        bench_name = b[0]
        res_type = b[1]
        results = b[2]
        value = 0
        if res_type == "SimpleComparisonResult":
            if changed:
                value = results['changed_time']
            else:
                value = results['base_time']
        elif res_type == "ComparisonResult":
            if changed:
                value = results['avg_changed']
            else:
                value = results['avg_base']
        else:
            print("ERROR: result type unknown " + b[1])
            return 1
        data = {
            'commitid': revision,
            'project': project,
            'executable': interpreter,
            'benchmark': bench_name,
            'environment': host,
            'result_value': value,
        }
        if res_type == "ComparisonResult":
            if changed:
                data['std_dev'] = results['std_changed']
            else:
                data['std_dev'] = results['std_base']
        if testing: testparams.append(data)
        else: error |= send(data)
    if error:
        raise IOError("Saving failed.  See messages above.")
    if testing: return testparams
    else: return 0
    
def send(data):
    #save results
    params = urllib.urlencode(data)
    f = None
    response = "None"
    info = str(datetime.today()) + ": Saving result for " + data['executable'] + " revision "
    info += str(data['commitid']) + ", benchmark " + data['benchmark']
    print(info)
    try:
        f = urllib2.urlopen(SPEEDURL + 'result/add/', params)
        response = f.read()
        f.close()
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            response = '\n  We failed to reach a server\n'
            response += '  Reason: ' + str(e.reason)
        elif hasattr(e, 'code'):
            response = '\n  The server couldn\'t fulfill the request'
        print("Server (%s) response: %s" % (SPEEDURL, response))
        print('  Error code: %s\n' % (e,))
        return 1
    print "saved correctly!\n"
    return 0

