"""
This script will crawl through an input SSC directory and serialize the
stepcharts in the .ssc files.

To use this script, run it from the command line. You will be prompted
to enter the path to your ssc directory, the names of the pack folders
you wish to crawl through, and the name of the .csv file you wish to
output. The script will then parse the .ssc files within the input pack
folders and parse any Pump It Up single or double stepcharts found.
Nonstandard charts, such as unofficial charts or quest charts, will be
ignored. The steps of each chart will be serialized, and the script
will save a .csv file in the data subfolder of the NLPump directory.
The rows of the .csv file correspond to stepcharts, and the columns
give the song title, step type (single or double), difficulty, and the
serialized steps.
"""
import os, re
import pandas as pd
from ssc_parser import SSCFile
from stepchart_parser import Stepchart
from step_serializer import StepSerializer


def get_item_paths(folder: str) -> list[str]:
    """
    Returns the paths to all items found in the input directory.

    Raises an error if the input folder is not a directory.

    Arguments
    ---------
    folder : str
        The path to a directory.
    """
    # Raise an error if the input folder is not a directory.
    if not os.path.isdir(folder):
        raise ValueError(f'{folder} is not a valid directory.')
    list_dir = os.listdir(folder)
    paths = [os.path.join(folder, subfolder) for subfolder in list_dir]

    return paths


def get_subfolders(folder: str) -> list[str]:
    """
    Returns the subfolders of an input directory.

    Arguments
    ---------
    folder : str
        The path to a directory.

    Returns
    -------
    subfolders : filter
        Yields the subfolders of the input folder.
    """
    subfolders = filter(os.path.isdir, get_item_paths(folder))

    return subfolders


def get_sscs(folder: str) -> filter:
    """
    Returns the .ssc files in an input directory.

    Arguments
    ---------
    folder : str
        The path to a directory.

    Returns
    -------
    sscs : filter
        Yields the .ssc files in the input folder.
    """
    check_ssc = lambda s: re.match('.*\.ssc$', s)
    sscs = filter(check_ssc, get_item_paths(folder))

    return sscs


def crawl(folder: str, valid_packs: list=[], verbose: bool=True) -> list[str]:
    """
    Find all .ssc files in subfolders of the input directory.

    The function assumes that the input directory contains 'pack
    folders', each of which contains 'song folders' which contain the
    .ssc files, i.e. the .ssc files are located exactly 2
    subdirectories down from the input directory. The arguments can be
    set to search only in specific pack folders or to search in all
    subfolders of the parent directory.

    Raises an error if the input path is not a directory.

    Arguments
    ---------
    folder : str
        A path to the parent directory to search in.
    valid_packs : list[str]
        A list of pack folders. If empty, all subfolders of the parent
        directory will be searched. Otherwise, only packs in
        valid_packs will be searched.
    verbose : bool
        If true, the function will print status updates such as the
        number of .ssc files found in each pack folder.

    Returns
    -------
    all_sscs : list[str]
        A list of paths to all .ssc files found.
    """
    # Raise an error if the input path is not a directory.
    if not os.path.isdir(folder):
        raise ValueError(f'{folder} is not a valid directory.')

    if verbose:
        print(f'Searching for .ssc files in {folder} ...')

    # Get all .ssc files from each pack.
    all_sscs = []
    for pack in get_subfolders(folder):
        # Check if pack is in the desired search list.
        pack_name = pack.split(os.path.sep)[-1]
        if valid_packs and pack_name not in valid_packs:
            continue

        sscs = []
        count = 0
        for song in get_subfolders(pack):
            for ssc in get_sscs(song):
                count += 1
                sscs.append(ssc)
        all_sscs.extend(sscs)
        # Print the numebr of .ssc files found in the pack.
        if verbose:
            print(f'\tFound {count} .ssc files in {pack}')

    # Print the total number of .ssc files found.
    if verbose:
        print()
        print(f'Search done. Found {len(all_sscs)} .ssc files in {folder}')

    return all_sscs


if __name__ == '__main__':
    # Prompt the user to enter their .ssc directory.
    ssc_directory = str(input('Enter the path to your SSC directory: '))
    print()

    # Raise an error if the input directory is invalid.
    if not os.path.isdir(ssc_directory):
        raise ValueError(f'{ssc_directory} is not a valid directory.')

    # Prompt the user to enter a list of packs.
    prompt = '''
        Enter a list of song pack names, separated by commas. If you wish to
        parse all song packs in your SSC directory, enter a null argument: 
    '''
    prompt = re.sub('\s+', ' ', prompt.lstrip())
    packs = str(input(prompt)).split(',')
    if len(packs) == 1 and len(packs[0]) == 0:
        packs.clear()
    print()

    # Prompt the user to enter a file name for the resulting .csv file.
    prompt = '''
        Enter a file name for the .csv file to be produced (do not include the
        extension): 
    '''
    prompt = re.sub('\s+', ' ', prompt.lstrip())
    file_name = str(input(prompt))
    data_folder = os.path.join(os.path.dirname(os.getcwd()), 'data')
    csv_path = os.path.join(data_folder, f'{file_name}.csv')
    print()

    # Crawl through the .ssc directory and serialize steps.
    serializer = StepSerializer()
    sscs = crawl(ssc_directory, valid_packs=packs)
    all_chart_data = []
    for ssc in sscs:
        ssc = SSCFile(ssc)
        song_title = ssc.global_attributes['TITLE']
        for chart in ssc.stepcharts:
            # Parse the stepchart and serialize steps.
            chart = Stepchart(song_title, chart)
            if chart.standard:
                step_type = chart.format
                difficulty = chart.difficulty
                df = chart.chart_to_df()
                steps = serializer.serialize_steps(step_type, df)
                data = [song_title, step_type, difficulty, steps]
                all_chart_data.append(data)
                print(f'Serialized {song_title} {step_type}{difficulty}.')
        print()

    # Create and save stepchart data.
    df = pd.DataFrame(
        data=all_chart_data,
        columns=['Song Title', 'Step Type', 'Difficulty', 'Steps']
    )
    df.to_csv(csv_path, index=False)