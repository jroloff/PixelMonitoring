import datetime as dt


def get_date_from_era(era):
    era_to_date = {
        "2011": "Mar 2011 - Dec 2011",
        "2012": "Apr 2012 - Dec 2012",
        "2013": "Jan 2013 - Feb 2013",
        "2015": "June 2015 - Nov 2015",
        "2016": "Apr 2016 - Dec 2016",
        "2017": "May 2017 - Dec 2017",
        "2018": "Apr 2018 - Dec 2018",
        "run1": "Mar 2011 - Feb 2013",
        "run2": "June 2015 - Dec 2018",
        "run3": "July 2022 - Nov 2022",
        "run1_and_run2": "Mar 2011 - Dec 2018",
    }
    return era_to_date[era]


def get_phase_from_fill(fill):
    if not isinstance(fill, int):
        fill = int(fill)

    if fill >= 1005 and fill <= 5575:
        return 0
    elif fill >= 5698:
        return 1
    else:
        raise ValueError(f"Invalid fill number {fill}")
    

def get_phase_from_time(time):
    """
    Args:
        time (datetime)
    
    Returns:
        int
    """

    if time < dt.datetime(2016, 12, 6):
        return 0
    elif time >= dt.datetime(2017, 5, 23):
        return 1
    else:
        raise ValueError(f"Invalid time {time}")


def get_fills_for_era(era):
    """
    Args:
        era (str): Allowed eras are years (in the YYYY format) or run number
            (in the format run_X)
    
    Returns:
        list[int]
    """

    fills_2012 = list(range(3114, 3819))
    fills_2015 = list(range(3819, 4851))
    fills_2016 = list(range(4851, 5457))
    fills_2017 = list(range(5698, 6468))
    fills_2018 = list(range(6468, 7495))
    fills_2022 = list(range(7920, 8497))
    fills_run1 = fills_2012
    fills_run2 = fills_2015 + fills_2016 + fills_2017 + fills_2018
    fills_run3 = fills_2022
    fills_run1_and_run2 = fills_2015 + fills_2016 + fills_2017 + fills_2018

    return eval("fills_" + era)


def get_run_number_from_fill(fill):
    """
    Args:
        fill (int)
    
    Returns:
        int
    """

    for run_number in range(1, 4):
        if fill in get_fills_for_era("run" + str(run_number)):
            return run_number
    
    raise ValueError("Fill number outside of valid range!")


def get_pp_cross_section(fill):
    """Return proton-proton non-fiducial cross-section in mb.
    
    Args:
        fill (int)
    
    Returns:
        float
    """

    run_number = get_run_number_from_fill(fill)
    if run_number == 2:
        return 79.1
    elif run_number == 3:
        print("Warning: Run3 pp cross-section should be updated!")
        return 80  # No idea how much it is, but it is not much more
    else:
        raise NotImplementedError

