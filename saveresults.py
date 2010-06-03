# -*- coding: utf-8 -*-
#######################################################
# This script saves result data                       #
# It expects the format of unladen swallow's perf.py  #
#######################################################
import urllib, urllib2
from datetime import datetime

SPEEDURL = "http://speed.pypy.org/"

def save(project, revision, results, options, branch, interpreter,
         int_options, host, testing=False):
    testparams = []
    #Parse data
    data = {}
    current_date = datetime.today()
    error = 0
        
    for b in results:
        bench_name = b[0]
        res_type = b[1]
        results = b[2]
        value = 0
        if res_type == "SimpleComparisonResult":
            value = results['changed_time']
        elif res_type == "ComparisonResult":
            value = results['avg_changed']
        else:
            print("ERROR: result type unknown " + b[1])
            return 1
        data = {
            'commitid': revision,
            'project': project,
            'executable_name': interpreter,
            'executable_coptions': int_options,
            'benchmark': bench_name,
            'environment': host,
            'result_value': value,
            'result_date': current_date,
        }
        if res_type == "ComparisonResult":
            data['std_dev'] = results['std_changed']
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
    info = str(datetime.today()) + ": Saving result for " + data['executable_name'] + " revision "
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
        print("Server (%s) response: %s\n" % (SPEEDURL, response))
        print('  Error code: ' + str(e))
        return 1
    print "saved correctly!\n"
    return 0

