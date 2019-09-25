# Most imports are done only in the functions, so that the program doesn't break if modules are not installed when not running the parallel scenario

import time
import sys
import io



def start_name_server(verbose=False):
    """
    Starts a pyro name server

    Args:
        verbose: If False output of the server is suppressed. This is usually desirable to avoid spamming the console window.
    """
    import Pyro4
    if not verbose:
        # create a text trap and redirect stdout
        text_trap = io.StringIO()
        sys.stdout = text_trap

    Pyro4.naming.startNSloop()

    if not verbose:
        # now restore stdout function
        sys.stdout = sys.__stdout__


def start_dispatch_server(verbose=False):
    """
    Starts a pyro dispatch server

    Args:
        verbose: If False output of the server is suppressed. This is usually desirable to avoid spamming the console window.
    """
    from pyutilib.pyro import DispatcherServer
    if not verbose:
        # create a text trap and redirect stdout
        text_trap = io.StringIO()
        sys.stdout = text_trap

    dispatch_srvr = DispatcherServer()

    if not verbose:
        # now restore stdout function
        sys.stdout = sys.__stdout__


def start_pyro_mip_server(verbose=False):
    """
    Starts a pyro worker

    Args:
        verbose: If False output of the server is suppressed. This is usually desirable to avoid spamming the console window.
    """
    from pyomo.scripting.pyro_mip_server import main as pyro_mip_server
    if not verbose:
        # create a text trap and redirect stdout
        text_trap = io.StringIO()
        sys.stdout = text_trap

    pyro_mip_server()

    if not verbose:
        # now restore stdout function
        sys.stdout = sys.__stdout__


def pyro_safety_abort():
    """
    Check if there is a pyro name server running, which indicates that another program using pyro might be running.
    This might lead to unexpected behaviour, unexpected shutdowns of some of the servers or unexpected crashes in any of the programs.
    To avoid problems the program which called this function fails with an Exception.
    """
    import Pyro4
    try:
        Pyro4.locateNS()
    except:
        return
    raise Exception(
            'A Pyro4 name server is already running,'
            ' this indicates that other programs using Pyro are already running,'
            ' which might lead to crashes in any of the programs.'
            ' To avoid this, this program is aborted.'
            ' If you want to run anyway, put run_safe to False and run again.')


def start_pyro_servers(number_of_workers=None, verbose=False, run_safe=True):
    """
    Starts all servers necessary to solve instances with Pyro. All servers are started as daemons, s.t. if the main thread terminates or aborts, the servers also shutdown.

    Args:
        number_of_workers: number of workers which are started. Default value is the number of cores.
        verbose: If False output of the servers is suppressed. This is usually desirable to avoid spamming the console window.
        run_safe: If True a safety check is performed which ensures no other program using pyro is running.

    Returns: list of processes which have been started so that they can later be shut down again
    """
    from multiprocessing import Process
    # safety check to ensure no program using pyro is currently running
    if run_safe:
        pyro_safety_abort()
    # launch servers from code
    process_list = []
    # name server
    p = Process(target=start_name_server,kwargs={'verbose':verbose})
    p.daemon = True
    process_list.append(p)
    p.start()
    # dispatch server
    p = Process(target=start_dispatch_server,kwargs={'verbose':verbose})
    p.daemon = True
    process_list.append(p)
    p.start()
    # workers
    # TODO: Is there a better default value?
    if number_of_workers is None:
        from multiprocessing import cpu_count
        number_of_workers = cpu_count()
    for i in range(0, number_of_workers):
        p = Process(target=start_pyro_mip_server,kwargs={'verbose':verbose})
        p.daemon = True
        process_list.append(p)
        p.start()
    # wait shortly to give servers time to start
    time.sleep(5)
    return process_list


def shutdown_pyro_servers(process_list):
    """
    Terminates all processes in process_list

    Args:
        process_list: processes to be terminated
    """
    # shutdown servers
    for p in process_list:
        p.terminate()


def solve_parallel(instances, solver, verbose=False):
    """
    Solves pyomo model instances in parallel using pyro

    Args:
        instances: instances dict
        solver: solver to be used for the problems
        verbose: If False output of the clients is suppressed. This is usually desirable to avoid spamming the console window.

    Returns:
        A list of the solver results
    """
    if not verbose:
        # create a text trap and redirect stdout
        oldstdout = sys.stdout
        text_trap = io.StringIO()
        sys.stdout = text_trap

    from pyomo.opt.parallel import SolverManagerFactory

    solver_manager = SolverManagerFactory('pyro')
    if solver_manager is None:
        print("Failed to create solver manager.")
        sys.exit(1)

    action_handle_map = {}  # maps action handles to instances
    for i, inst in enumerate(instances):
        action_handle = solver_manager.queue(instances[inst], opt=solver, tee=False)
        action_handle_map[action_handle] = "inst_{}".format(i)

    # retrieve the solutions
    results = []
    for i in range(0, len(instances)):  # we know there are two instances
        this_action_handle = solver_manager.wait_any()
        results.append(solver_manager.get_results(this_action_handle))

    if not verbose:
        # now restore stdout function
        sys.stdout = oldstdout

    return results


#TODO: If not used, delete
def parallel_threads(f,argslist):
    """
    Method that starts an arbitrary function f in parallel in the following way: f(argslist[1]), f[argslist[2]),...,f(argslist[len(argslist)-1]

    Args:
        f: a pointer to a function
        argslist: a list of tuples. One tuple gives the arguments passed to f for one function call.
    Returns:
        The results of the functions as a list
    """
    from threading import Thread
    import queue
    result=[]
    que = queue.Queue()
    threads_list = list()

    for i in range(0, len(argslist)):
        t = Thread(target=lambda q, args: q.put(f(*args)),
                   args=(que, argslist[i]))
        t.start()
        threads_list.append(t)
    # Join all the threads
    for t in threads_list:
        t.join()

    # Check thread's return value
    while not que.empty():
        res = que.get()
        result.append(res)
    return result


#TODO: If not used, delete
def parallel_processes(f,argslist):
    """
    Like parallel_threads, but with processes. Difference is that processes do not share the same memory space, but are more flexible.
    Doesn't support return at the moment.

    Args:
        f: a pointer to a function
        argslist: a list of tuples. One tuple gives the arguments passed to f for one function call.

    """
    from multiprocessing import Process
    process_list = list()

    for i in range(0, len(argslist)):
        p = Process(target=f, args=(argslist[i]))
        p.start()
        process_list.append(p)
    # Join all the processes
    for p in process_list:
        p.join()

