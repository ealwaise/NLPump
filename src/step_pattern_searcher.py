'''
This module contains the StepPatternSearcher class, which can be used to search
for patterns within Pump It Up stepcharts.
'''

import re

class StepPatternSearcher:
    '''
    This class can find step patterns within a Pump It Up stepchart.

    This class searches for step patterns within a serialized stepchart by
    using regular expressions. One can specify a range of speeds at which the
    patter should occur.
    '''
    num_pattern = '[0-9\.]+' # Used to pick up timestamps in the chart.
    order = 'ZQSECVRGYNzqsecvrgyn' # Used for sorting steps.
    mirrors = { # Used for mirroring patterns.
        'S': {
            'Z': 'C',
            'Q': 'E',
            'S': 'S',
            'E': 'Q',
            'C': 'Z',
            'z': 'c',
            'q': 'e',
            's': 's',
            'e': 'q',
            'c': 'z',
        },
        'D': {
            'Z': 'N',
            'Q': 'Y',
            'S': 'G',
            'E': 'R',
            'C': 'V',
            'V': 'C',
            'R': 'E',
            'G': 'S',
            'Y': 'Q',
            'N': 'Z',
            'z': 'n',
            'q': 'y',
            's': 'g',
            'e': 'r',
            'c': 'v',
            'v': 'c',
            'r': 'e',
            'g': 's',
            'y': 'q',
            'n': 'z'
        }
    }

    def get_regex_pattern(
        self,
        step_pattern: str,
        hold_distinctions: bool
    ) -> list[str]:
        '''
        Convert an input step pattern into a regular expression.

        To convert the step pattern into a regular expression, expressions
        which correspond to the colon separator and the timestamps found in a
        serialized stepchart need to be added. Characters corresponding to
        panels are sorted so that searches do not dependent on the order in
        which panels are written in the input pattern.

        Parameters
        ----------
        step_pattern : str
            A string representing the step pattern to search for.
        hold_distinctions : bool
            If true, the caps/tails/interiors of holds will be distinguished
            for searching.

        Returns
        -------
        pattern : str
            A list containing timestamps at which the pattern can be found. 
        '''
        pattern = []
        notes = step_pattern.split('-')

        # Iterate through notes and construct regular expression pattern.
        for i, steps in enumerate(notes):
            # Sort steps so the order in which they are typed is irrelevant.
            steps = sorted(steps, key=lambda c: self.order.index(c))

            # Prevents hold caps/tails/interiors from being distinguished.
            if not hold_distinctions:
                for j, step in enumerate(steps):
                    if step.islower():
                        steps[j] = f'{step}[0-1]{{0,1}}'
            steps = ''.join(steps)
            subpattern = f'{self.num_pattern}:{steps}'
            pattern.append(subpattern)

        pattern = '-'.join(pattern)

        return pattern

    def search(
        self,
        step_type: str,
        chart: str,
        step_pattern: str,
        min_dt: float=0.0,
        max_dt: float=1.0,
        tol: float=.01,
        hold_distinctions: bool=False
    ) -> list[float]:
        '''
        Search a chart for a step pattern within a speed range.

        This function can search for a step pattern, defined as a sequence of
        steps separated by a constant amount of time. The input step pattern is
        converted into a reuglar expression used to search a serialized
        stepchart. The output is a list of timestamps which indicate points at
        which the input pattern occurs within the chart.

        Parameters
        ----------
        step_type : str
            Equal to 'S' if the chart is a singles chart or 'D' if the chart is
            a doubles chart.
        chart : str
            A serialized stepchart.
        step_pattern : str
            A string representing the step pattern to search for.
        min_dt : float
            The minimum time differential between steps in the pattern.
        max_dt : float
            The maximum time differential between steps in the pattern.
        hold_distinctions : bool
            If true, the caps/tails/interiors of holds will be distinguished
            for searching.
        tol : float
            A tolerance parameter controlling how close the time differentials
            between steps need to be to the input range.

        Returns
        -------
        timestamps : list[float]
            A list containing timestamps at which the pattern can be found. 
        '''
        # Get regular expression pattern and find possible matches.
        pattern = self.get_regex_pattern(step_pattern, hold_distinctions)
        possible_matches = re.findall(pattern, chart)

        # Find possible matches for the mirrored pattern if it's different.
        mirrored_step_pattern = ''.join(
            [self.mirrors[step_type].get(char, char) for char in step_pattern]
        )
        if mirrored_step_pattern != step_pattern:
            mirrored_pattern = self.get_regex_pattern(
                mirrored_step_pattern,
                hold_distinctions
            )
            possible_matches.extend(re.findall(mirrored_pattern, chart))

        # Retain only matches satisfying the speed constraints.
        timestamps = []
        for match in possible_matches:
            valid = True
            notes = match.split('-')
            if len(notes) > 1:
                time_delta = -1
                prev_time = float(notes[0].split(':')[0])
                for note in notes[1:]:
                    time = float(note.split(':')[0])
                    dt = time - prev_time
                    # Check if time differential is in required range.
                    if time_delta >= 0 and (abs(dt - time_delta) > tol or \
                        dt < min_dt - tol or dt > max_dt + tol):
                        valid = False
                        break

                    prev_time = time
                    time_delta = dt
            # Add timestamp if the match satisfies the time constraints.
            if valid:
                timestamp = float(match.split('-')[0].split(':')[0])
                timestamps.append(timestamp)

        return timestamps