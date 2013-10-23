'''
Created on 04/02/2013

@author: victor
'''
import optparse
import threading
from pyproclust.driver.parameters import ProtocolParameters
from pyproclust.driver.observer.observer import Observer
from pyproclust.driver.driver import Driver

class CmdLinePrinter(threading.Thread):
    
    def __init__(self,data_source):
        super(CmdLinePrinter, self).__init__()
        self._stop = threading.Event()
        self.data_source = data_source
        
    def stop(self):
        self._stop.set()
        self.data_source.notify("Main","Stop","Finished")

    def stopped(self):
        return self._stop.isSet()
    
    def run(self):
        while not self.stopped():
            self.data_source.wait()
            print self.data_source.get_data()
            self.data_source.clear()

if __name__ == '__main__':
    parser = optparse.OptionParser(usage='%prog [--mpi] [--gui] script', version='1.0')
    
    parser.add_option('--mpi', action="store_true",  dest = "use_mpi", help="Add this flag if you want to use MPI-based scheduling.")
    parser.add_option('--print', action="store_true",  dest = "print_messages", help="Add this flag to print observed messages to stdout.")
    
    options, args = parser.parse_args()
    
    if(len(args)==0):
        parser.error("You need to specify the script to be executed.")

    json_script = args[0]
    
    parameters = None
    try:
        parameters = ProtocolParameters.get_params_from_json(open(json_script).read())
    except ValueError, e:
        print "Malformed json script."
        print e.message
        exit()
    
    observer = None
    cmd_thread = None
    if options.use_mpi:
        from pyproclust.driver.mpidriver import MPIDriver
        from pyproclust.driver.observer.MPIObserver import MPIObserver
        observer = MPIObserver()
        if options.print_messages:
            cmd_thread = CmdLinePrinter(observer)
            cmd_thread.start()
        MPIDriver(observer).run(parameters)
    else:
        observer = Observer()
        if options.print_messages:
            cmd_thread = CmdLinePrinter(observer)
            cmd_thread.start()
        Driver(observer).run(parameters)
    
    if options.print_messages:    
        cmd_thread.stop()
