import os
import shutil
import psutil
from pathlib import Path
import subprocess
import random
import string
import asyncio
from datetime import datetime
import time
import yaml

import click

plots = []
#plot_size = 70000000000 # byte
plot_size = 42000000 # byte
is_running = False
max_concurrent = 1
bwlimit = 100000
configPath = 'config.yaml'

# global to keep track of all the plots moved, so i can check if i placed already in the queue.
# we can eliminate by using some os call when new files arrive
plots_archive = []

# unit
space_unit_size = {'Mb': 1024**2, 'Gb': 1024**3, 'Tb': 1024**4}
sel_unit = 'Gb'
unit = {'size' : sel_unit, 'factor' : space_unit_size[sel_unit]}

info_move_active = []
info_delete_active = []

# Load logging file
loggingPath = 'debugRoto.log'

# i should check that dest suffix is not in obsolete dir to avoid problems

#plots_dir.append("/mnt/intelRock/")
#plots_dir.append("/home/boon/plotting_folder01/")
#plots_dir.append("/home/boon/plotting_folder02")


#destination_dir.append("/mnt/dinothrfarm/na62_hgst01")
#destination_dir.append("/mnt/dinothrfarm/na62_hgst02")
#destination_dir.append("/mnt/sm487_01")
#destination_dir.append("/mnt/sm487_02/")
#destination_dir.append("/mnt/sm487_03")
#

#
#@click.command()
#@click.option('--sources',
#              prompt='plotting directories',
#              help='the list of plotting directories or a path to a file.')
#@click.option('--destinations',
#              prompt='destination directories',
#              help='the list of the final directories for plots or a path to a file.')
#
#def printCmd(sources, destinations):
#    click.echo(f"I am running with plotting source: {sources} and destination: {destinations}")

class ConfigParam:
    def __init__(self):
        self.is_running = False
        self.plot_size = 0
        self.plots_dir = []
        self.destination_dir = []
        self.dest_suffix = ''
        self.obsolete_dir = []
        self.max_concurrent = 1
        self.bwlimit = 0

def loadYamlConfig(configPath, config):
    """Load YAML data. """
    with open(configPath, 'r') as file:
        data = yaml.safe_load(file)

    config.is_running = data['running']
    config.plot_size = data['plot_size']
    config.plots_dir = data['plot_directories']
    config.destination_dir =data['destination_directories']
    config.dest_suffix = data['destination_suffix']
    config.obsolete_dir = data['obsolete_folder']
    config.max_concurrent = data['max_concurrent']
    config.bwlimit = data['rsync_bw_limit']
    config.debugging = data['debugging']


log_lock = asyncio.Lock()
async def logging(*args):
    timestamp = datetime.now().isoformat(timespec='seconds')
    str_message = timestamp + ' '
    for arg in args:
        str_message += str(arg)
    str_message += '\n'

    async with log_lock:
        with open(loggingPath, 'a') as logFile:
            logFile.write(str_message)

def findPlots(sources):
    for source in sources:
        for plot in Path(source).glob("*.plot"):
            plots.append(plot)

def movePlot(plot, destination):
    # add delete option
    cmd = ['rsync', '-av', '--bwlimit=1000', '--remove-source-files',  plot, destination]
    subprocess.run(cmd)

def freeSpace(path):
    return shutil.disk_usage(path).free

# find folder space
async def get_dir_size(path):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += await get_dir_size(entry.path)
    return total

async def get_dir_size_noSub(path):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
    return total

async def findPlotsA(sources, plots_queue):
    for source in sources:
        for plot in Path(source).glob("*.plot"):
            if plot in plots_archive:
                await logging(plot)
                continue
            await plots_queue.put(plot)
            plots_archive.append(plot)

async def evaluateDestinations(destinations, dest_queue, obsolete_queue, obsolete_folders=None):
    # shuld i add the ability to rescan ?
    for path in destinations:
        path = Path(path)
        if freeSpace(path) < plot_size:
           if obsolete_folders:
                obsolete_folders_number = len(obsolete_folders)
                for folder in obsolete_folders:
                    path_folder = path.joinpath(folder)
                    await logging(path_folder)
                    if path_folder.exists():
                        size = await get_dir_size_noSub(path_folder)
                        if size != 0:
                            await obsolete_queue.put(path)
                            await logging(f"The disk: {path} is full, but it can be emptied of {size / unit['factor']} {unit['size']}")
                            break
                    else:
                        obsolete_folders_number -= 1
                        await logging(f"The disk: {path} has no subfolder {folder}")
                        if obsolete_folders_number == 0:
                            await logging(f"The disk: {path} is full.")
           else:
                await logging(f"The disk: {path} is full.")
        else:
            await dest_queue.put(path)

async def replantPlots(dest_queue, dest_suffix, obsolete_queue, plots_queue, bwlimit):

    # IF there is free space, lets fill first
    await logging("replant starting...")
    error = "EE_"
    try:
        if not dest_queue.empty():
            dest_root = await dest_queue.get()
            #if not dest_root.is_mount():
            #    await logging(f"The {dest_root} destination is not mounted, the destination will be dropped")
            #    return 0
            if False:
                await logging("not possible I am printed")
            else:
                plot = await plots_queue.get()
                plot_size = plot.stat().st_size
                await logging(f'plot size {plot_size}')
                dest = dest_root.joinpath(dest_suffix)
                error = error + str(dest) + str(plot)
                if not dest.exists():
                    dest.mkdir(exist_ok=False)

                if freeSpace(dest) > plot_size:
                    # move
                    await logging(f"replant: moving to this destination: {dest}")
                    await movePlotA(plot, dest, bwlimit)
                    await logging(f"plot moved to {dest}")
                    await dest_queue.put(dest_root)
                else:
                    # here something should happen? like it exit from the queue, and then
                    # it will be pick up again if it is eligible to deleto old plots?
                    await plots_queue.put(plot)
                    await obsolete_queue.put(dest_root)
                    await logging(f"The {dest_root} destination is full, the destination will be dropped,\
                    if there are old plots that can be canceled it will be pick up again.")
    except Exception as e:
        await logging(f"something wrong with the replant: {e}")
        with open(error, "w") as f:
            f.write(error)
            f.write("error")
            f.write(e)
            f.write("END")
            f.close()
        await plots_queue.put(plot)
        await dest_queue.put(dest_root)
    except KeyboardInterrupt:
        await logging("who stoppped my replant pressing a key?")
        await plots_queue.put(plot)
        await dest_queue.put(dest_root)
        pass


        

    # If the dest queue has less then the limit moves, lets empty the
    # number of drives that we move plus 2 drives, put the drives in the dest_queue
    #
    return 0

async def movePlotA(plot, destination, bwlimit):
    """Move a file from source to destination directory."""
    cmd = f"ionice -c 3 rsync -v --preallocate --whole-file --bwlimit={bwlimit} --remove-source-files {plot} {destination}"
    #cmd = f"mv -v {plot} {destination}"
    await logging(f"MOVING {plot}")
    await logging(f"to {destination}")
    global info_move_active

    try:
        info_move_active.append(cmd)
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        start = datetime.now()
        stdout, stderr = await proc.communicate()
        finish = datetime.now()
        info_move_active.remove(cmd)

        if proc.returncode != 0:
            await logging(f"ERROR CODE {proc.returncode}")
            with open(cmd, "w") as f:
                f.write(cmd)
                f.write("error")
                f.write(f"ERROR CODE {proc.returncode}")
                f.write("END")
                f.close()
        if proc.returncode == 0:
            await logging(f"Finished the move to {destination} in {finish - start} seconds.")
    except Exception as e:
        await logging(f'ERROR {e} in movePlotA')
          
        with open(cmd, "w") as f:
            f.write(cmd)
            f.write("error")
            f.write(e)
            f.write("END")
            f.close()

async def deleteObsoletePlots(obsolete_queue, obsolete_folders, dest_queue, max_concurrent):
    await logging("inside the obsolete oblivion")
    while dest_queue.qsize() < max_concurrent or obsolete_queue.empty() != False:
        await logging("inside the while delete")
        path = Path(await obsolete_queue.get())
        for folder in obsolete_folders:
            path_folder = path.joinpath(folder)
            if path_folder.exists():
                await logging(f'the plot folder is {path_folder}')
                with os.scandir(path_folder) as files:
                    count = 0
                    for entry in files:
                        if entry.is_file() and Path(entry.name).suffix == '.plot':
                            await logging("inside")
                            await logging(entry.name)
                            try:
                                await logging("plot to delete is:")
                                await logging(entry)
                                file_path = entry.path
                                await logging(file_path)
                                await logging("DELETING")
                                info_delete_active.append(file_path)
                                await asyncio.sleep(0)  # Allow other tasks to run
                                os.remove(file_path)
                                await logging("file deleted")
                            except Exception as e:
                                await logging(f'an error happend deleting {file_path}')
                                await logging(f'the exception is: {e}')
                            finally:
                                await asyncio.sleep(5)
                                await logging("obsolete oblivion awaited")
                                info_delete_active.remove(file_path)
                                count += 1
                                if freeSpace(path) > (2 * plot_size):
                                    await logging("breaked the oblivion")
                                    break
                    if count != 0:
                        await logging('added a new disk into the destination queue')
                        await dest_queue.put(path)

async def updateConfig(configPath, config):
    loadYamlConfig(configPath, config)

async def main(config):
    # get the loop
    loop = asyncio.get_running_loop()

    # init the queue
    dest_queue = asyncio.Queue()
    obsolete_queue = asyncio.Queue()
    plots_queue = asyncio.Queue()
    await evaluateDestinations(config.destination_dir, dest_queue, obsolete_queue, config.obsolete_dir)
    await findPlotsA(config.plots_dir, plots_queue)

    await logging(f'Dest queue {dest_queue}')
    await logging("")
    await logging(f'obsolete queue {obsolete_queue}')
    await logging("")
    await logging("plots archive")
    await logging(plots_archive)

    terminal_size = os.get_terminal_size()
    start_time = time.time()


    tasks = []
    d_tasks = []


    while config.is_running:

        await logging("checking update config")
        await updateConfig(configPath, config)

        # DEBUGGING: clear the terminal
        # create a config variable for debugging the interface? so there is only
        # one place to change
        if not config.debugging:
            os.system('cls' if os.name == 'nt' else 'clear')

        print()
        print(f'Dest queue:     {dest_queue.qsize()}')
        print(f'Obsolete queue: {obsolete_queue.qsize()}')
        print(f'Plots queue:    {plots_queue.qsize()}')
        print()
        print(f'Number of full disks with old plots: {obsolete_queue.qsize()}')
        print()
        print(f"Terminal width: {terminal_size.columns} characters")
        print(f"Terminal height: {terminal_size.lines} lines")
        print()
        print(f'Time elapsed: {time.time() - start_time}')
        print("Active moving")
        for i in info_move_active:
            print(i)
        print("Active deleting")
        for i in info_delete_active:
            print(i)
        start_time = time.time()
        print()
        print(f'is running: {is_running}')
        print("_________real time logs_________")

        # delete plots
        print("the bool value")
        print(obsolete_queue.qsize() != 0 and dest_queue.qsize() <= config.max_concurrent)
        print(obsolete_queue.qsize())
        print(plots_queue.qsize())
        if obsolete_queue.qsize() != 0 and dest_queue.qsize() <= config.max_concurrent:
            try:
                # should i check here also the number of free disk?
                task = asyncio.create_task(deleteObsoletePlots(obsolete_queue, config.obsolete_dir,
                                                            dest_queue, config.max_concurrent))
                d_tasks.append(task)

                # Remove completed tasks
                for task in d_tasks:
                    if task.done():
                        d_tasks.remove(task)
            except Exception as e:
                await logging(f"something WRONG by creating free space: {e}")
            except KeyboardInterrupt:
                await logging("who enlighed my oblivion?")
            finally:
                await logging("new free space here... maybe")

        # check for new plots
        if plots_queue.qsize() < config.max_concurrent:
            await logging("checking for new plots")
            await logging("logging in the main")
            await findPlotsA(config.plots_dir, plots_queue)
        else:
            await logging("plots queue is greater then max_concurrent")
            await logging(plots_queue.qsize(), " queue size")
            await logging(config.max_concurrent, "max concurrent")

        # check if we capped
        if len(tasks) == config.max_concurrent or dest_queue.empty() or plots_queue.empty():
            await logging("lest rest hoping something will happen")
            await logging(f'plots queue: size {plots_queue.qsize()} and emptyness {plots_queue.empty()}')
            # Remove completed tasks
            for task in tasks:
                if task.done():
                    tasks.remove(task)
            await asyncio.sleep(10)
            continue
        try:

            await logging(f"Tasks running: {len(tasks)} of {config.max_concurrent}")
            task = asyncio.create_task(replantPlots(dest_queue, config.dest_suffix, obsolete_queue, plots_queue, config.bwlimit))
            tasks.append(task)

            # Remove completed tasks
            for task in tasks:
                if task.done():
                    tasks.remove(task)

            # Sleep for 1 second before checking for new files to move
            await asyncio.sleep(1)

        except Exception as e:
            await logging(f"something wrong in the main loop: {e}")
        except KeyboardInterrupt:
            await logging("who stoppped my replant?")
        finally:
            await logging("main loop done, take some time")
            await asyncio.sleep(10)


        await asyncio.sleep(5)
    await logging("ASPETTO FINE  TASK")
    # Wait for the tasks to complete
    await asyncio.gather(*tasks)
    await asyncio.gather(*d_tasks)

    await logging("esco dal giro")
    # Close the loop waiting for all the tasks
    loop.stop()
    await logging("uscito dal giro")


def createFakePlots():
    plotting_dir = [Path('/home/boon/plotting_folder01'), Path('/home/boon/plotting_folder02/')]
    src_path = Path('/home/boon/plotting_folder01/THEPLOT')
    prefix = 'plot_k32_'
    postfix = '.plot'

    # create plots
    for dir_p in plotting_dir:
        for i in range(100):
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))
            filename = ''.join([prefix,random_string,postfix])
            dest_path = dir_p.joinpath(filename)

            print(filename)
            print(dest_path)
            print(src_path)
            print()
            shutil.copy(src_path, dest_path)


    print(prefix, random_string, postfix)

def checkSourceAndDestination():
    # check that or the paths or the files with tha path are given at startup
    return 0

if __name__ == '__main__':

    # initialize the conf
    config = ConfigParam()
    loadYamlConfig(configPath, config)
    print(config.is_running)
    print(config.plots_dir)
    print(config.plot_size)
    print(config.destination_dir)
    print(config.dest_suffix)

    sources = config.plots_dir
    destinations = config.destination_dir
    obsolete_folders = config.obsolete_dir
    is_running = config.is_running


    #asyncio.run(main(sources, destinations, dest_suffix, max_concurrent, obsolete_folders, is_running))
    #asyncio.run(main(plots_dir, destination_dir, dest_suffix, max_concurrent, obsolete_dir, is_running))
    asyncio.run(main(config))



    print("totonno")
    print("totonno")
    print("totonno")
    print("totonno")
    print("totonno")
    exit()
    findPlots(sources)

    ## create plots
    #createFakePlots()

    print(plots)


    #for plot in plots:
    #    movePlot(plot, destination_dir[0])

    printCmd()
    printCmd(sources, destinations)

    printCmd()

exit()

###################################### async code ########################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
import asyncio
import os
import shutil
from pathlib import Path

async def move_file(source_file: Path, destination_dir: Path) -> None:
    """Move a file from source to destination directory."""
    await asyncio.sleep(1)  # Simulate some work
    shutil.move(str(source_file), str(destination_dir))

async def move_files(source_dir: Path, destination_dirs: list[Path]) -> None:
    """Move files from source directory to destination directories."""
    # Create a queue to hold the paths of the files to move
    file_queue = asyncio.Queue()

    # Start a task to monitor the source directory for new files to move
    async def monitor_dir():
        while True:
            # Get a list of files in the source directory
            files = list(source_dir.glob('*'))

            # Add any new files to the queue
            for file in files:
                if file not in file_queue._queue:
                    await file_queue.put(file)

            # Sleep for 1 second before checking for new files again
            await asyncio.sleep(1)

    asyncio.create_task(monitor_dir())

    # Start tasks to move files from the queue to the destination directories
    tasks = []
    while True:
        # Limit the number of files being moved simultaneously to 5
        while len(tasks) < 5 and not file_queue.empty():
            source_file = await file_queue.get()
            dest_dir = destination_dirs[file_queue.qsize() % len(destination_dirs)]
            task = asyncio.create_task(move_file(source_file, dest_dir))
            tasks.append(task)

        # Remove completed tasks
        for task in tasks:
            if task.done():
                tasks.remove(task)

        # Sleep for 1 second before checking for new files to move
        await asyncio.sleep(1)

if __name__ == '__main__':
    source_dir = Path('/path/to/source/dir')
    dest_dirs = [Path('/path/to/dest/dir1'), Path('/path/to/dest/dir2')]
    asyncio.run(move_files(source_dir, dest_dirs))

########################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
##########################################################################################
import asyncio
import os
import shutil

async def move_file(src, dest):
    print(f"Moving {src} to {dest}...")
    await asyncio.sleep(1) # simulate time it takes to move file
    shutil.move(src, dest)

async def move_files(source_dir, dest_dir, limit):
    file_queue = asyncio.Queue()

    # Populate the initial file queue with existing files in the source directory
    for filename in os.listdir(source_dir):
        src = os.path.join(source_dir, filename)
        dest = os.path.join(dest_dir, filename)
        file_queue.put_nowait((src, dest))

    while True:
        # Check if the limit has been reached
        while len(asyncio.all_tasks()) - 1 >= limit:
            await asyncio.sleep(1)

        # Scan the source directory for new files and add them to the queue
        for filename in os.listdir(source_dir):
            src = os.path.join(source_dir, filename)
            dest = os.path.join(dest_dir, filename)
            if not file_queue._queue.count((src, dest)):
                file_queue.put_nowait((src, dest))

        # Move the next file from the queue
        if not file_queue.empty():
            src, dest = await file_queue.get()
            await move_file(src, dest)
        else:
            await asyncio.sleep(1) # wait a bit before checking the queue again

async def main():
    source_dir = "/path/to/source/dir"
    dest_dir = "/path/to/dest/dir"
    limit = 5

    await move_files(source_dir, dest_dir, limit)

if __name__ == "__main__":
    asyncio.run(main())

########################################################################333





print('the size of / is')
size_root = get_dir_size('/home/')
print(f'root: {size_root / space_unit_size[unit]}GB')


#help(shutil)
#help(psutil)
diskUsage = psutil.disk_usage('/')

exit()

print(diskUsage.percent)
print(f'La percentuale è: {diskUsage.percent}%')
print(f'Total: {diskUsage.total / (1024 ** 3):.2f} GB')
print(f'Used: {diskUsage.used / (1024 ** 3):.2f} GB')
print(f'Free: {diskUsage.free / (1024 ** 3):.2f} GB')


# Get all mounted partitions
partitions = psutil.disk_partitions(all=True)

# Get disk I/O counters for all disks
disk_io_counters = psutil.disk_io_counters(perdisk=True)

# Loop through each partition and get the device information
for partition in partitions:
    if partition.fstype:
        usage = psutil.disk_usage(partition.mountpoint)
        device = partition.device
        try:
            for disk, io_counters in disk_io_counters.items():
                print(disk)
                print(device)
                print()
                device = device.split('/')

                if disk == device[-1]:
                    help(io_counters)
                    model = io_counters.serial_number
                    print(f"Model of {device}: {model}")
                    break
        except AttributeError:
            print(f"Model of {device}: Unknown")
