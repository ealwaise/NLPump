'''
This module contains the Stepchart class, which is used to parse the contents
of a Pump It Up stepchart and transform them into a tabular format.
'''

from functools import reduce
import re
import pandas as pd, numpy as np

class Stepchart:
    '''
    This class can parse the contents of a Pump It Up stepchart, including the
    notes and any timing effects. These contents can then be transformed into a
    .csv file which stores these contents along with corresponding timestamps.
    '''
    panel_map = [
        'Z',
        'Q',
        'S',
        'E',
        'C',
        'V',
        'R',
        'G',
        'Y',
        'N'
    ]
    step_type_map = {
        '1': 'tap',
        '2': 'hold (cap)',
        '3': 'hold (tail)',
        'F': 'fake',
        'M': 'mine',
        'L': 'lift'
    }
    timing_map = {
        'bpms': ['beat', 'bpm'],
        'stops': ['beat', 'stop'],
        'delays': ['beat', 'delay'],
        'warps': ['beat', 'warp'],
        'tickcounts': ['beat', 'tickcount'],
        'speeds': ['beat', 'speed', 'speed_duration', 'speed_mode'],
        'scrolls': ['beat', 'scroll_factor'],
        'fakes': ['beat', 'fake']
    }

    def __init__(self, song_title: str, stepchart: str):
        '''
        Parameters
        ----------
        song_title : str
            The title of the song.
        stepchart : str
            A parsed stepchart section of an .ssc file.
        '''
        attributes = stepchart['attributes']
        stepstype = attributes['STEPSTYPE']

        # Infer the number of panels based on the steptype.
        self.panels = 0
        self.format = 'unknown'
        if stepstype == 'pump-single':
            self.panels = 5
            self.format = 'S'
        elif stepstype == 'pump-double':
            self.panels = 10
            self.format = 'D'
        self.difficulty = int(attributes['METER'])
        self.title = f'{song_title} {self.format}{self.difficulty}'
        self.offset = float(attributes['OFFSET'])

        # Check if chart type should be excluded.
        description = attributes['DESCRIPTION']
        blacklist = [
            'UCS' in description,
            'QUEST' in description,
            'HIDDEN' in description,
            'HALF' in description,
            'SP' in description,
            'DP' in description,
            'INFINITY' in description,
            'TRAIN' in description
        ]
        self.standard = self.format in ['S', 'D'] and not any(blacklist) \
            and self.standard_notes(stepchart['notes'])

        # Get timing attributes and the notes section.
        self.timing_data = {
            'bpms': attributes['BPMS'],
            'stops': attributes.get('STOPS', ''),
            'delays': attributes.get('DELAYS', ''),
            'warps': attributes.get('WARPS', ''),
            'tickcounts': attributes['TICKCOUNTS'],
            'speeds': attributes['SPEEDS'],
            'scrolls': attributes['SCROLLS'],
            'fakes': attributes.get('FAKES', '')
        }
        self.notes = stepchart['notes']

    def standard_notes(self, notes: str) -> bool:
        '''
        Checks for any unusual notes in the stepchart.

        This function will return True if the stepchart contains only standard
        notes, meaning taps, holds, and fake notes. Mines, rolls, etc. are
        considered unusual and the function will return False if any such notes
        are detected.

        Parameters
        ----------
        notes : str
            A stepchart section from an .ssc file.

        Returns
        -------
        is_standard : bool
            True if the stepchart contains only standard notes, false
            otherwise.
        '''
        is_standard = True
        notes = re.split('\n+', notes.strip())
        note_pat = '[0-3F]*$' # Pattern note lines should match.

        # Check each note line and remove comments.
        for note in notes:
            note = note.strip()
            if note.startswith('//'):
                continue
            elif not note.startswith(','):
                note = note[:self.panels]
                if not re.match(note_pat, note):
                    is_standard = False
                    break

        return is_standard

    def parse_steps(self, notes: str) -> list:
        '''
        Parses the note data in the stepchart.

        The note data consists of measures, separated by commas. This function
        separates the measures and parses them in succession.

        Parameters
        ----------
        notes : str
            A stepchart section from an .ssc file.

        Returns
        -------
        steps : list[list]
            A 2D array containing all parsed steps in the stepchart.
        '''
        # Only consider pump single or double charts.
        if self.panels == 0:
            return []

        notes = re.split('\n+', notes.strip())
        clean_notes = []

        note_pat = '[0-3F]*$' # Pattern note lines should match.

        # Check each note line and remove comments.
        for note in notes:
            note = note.strip()
            if note.startswith(','):
                clean_notes.append(',')
            elif note.startswith('//'):
                continue
            else:
                note = note[:self.panels]
                # Set flag if a note doesn't match the usual pattern.
                if not re.match(note_pat, note):
                    self.standard = False
                    break

                clean_notes.append(note)
        notes = '\n'.join(clean_notes)

        # If the chart contains unusual notes, return an empty list.
        if not self.standard:
            return []

        # Loop through measures and parse notes.
        steps = []
        beat = 0
        measures = notes.split(',')
        for measure in measures:
            measure = measure.strip()
            parsed_measure = self.parse_measure(measure, beat)
            steps.extend(parsed_measure)
            beat += 4

        return steps

    def parse_measure(self, measure: str, beat: int) -> list[list]:
        '''
        Parses the measure occuring at a specific beat.

        A measure in an .ssc file consists of a number of lines. Each line
        contains n characters, where n is the number of panels. Each character
        indicate the presence of a step on the corresponding panel. This function
        iterates through the lines and parses them in succession.

        Parameters
        ----------
        measure : str
            Lines representing all steps within a measure.
        beat : int
            The beat at which the measure begins.

        Returns
        -------
        parsed_measure : list[list]
            A 2D list containing the parsed steps within the measure.
        '''
        notes = measure.split('\n')
        num_notes = len(notes)
        parsed_measure = []

        for note in notes:
            for panel, step_type in enumerate(note):
                if step_type != '0':
                    parsed_step = self.parse_step(panel, step_type, beat)
                    parsed_measure.append(parsed_step)
            beat += 4 / num_notes

        return parsed_measure

    def parse_step(self, panel: int, step: chr, beat: float) -> list:
        '''
        Parses an individual step.

        A step is a single character in a single line of the note data from an
        .ssc file. This function maps the character to the corresponding type
        of step (tap, hold cap, hold tail, etc.).
        
        Parameters
        ----------
        panel: int
            An index representing the panel being hit.
        step : str
            A digit corresponding to a type of step.
        beat : float
            The beat at which the step occurs

        Returns
        -------
        parsed_step : list
            A list containing the parsed step data.
        '''
        panel = Stepchart.panel_map[panel]
        step_type = Stepchart.step_type_map[step]
        parsed_step = [panel, step_type, beat]

        return parsed_step

    def parse_timing_changes(self, key: str, timing_data: str) -> list[list]:
        '''
        Parses timing changes found in the stepchart header attributes.

        The header of a stepchat section in an .ssc file contains various
        attributes which store timing changes, such as BPM changes or scroll
        effects. This function parses such an attribute, finding the beats at
        which the changes occur and the relevant values.

        Parameters
        ----------
        timing_data : str
            An attribute value containing all timing changes of a given type.

        Returns
        -------
        timing_changes : list[list]
            A 2D list containig the parsed timing changes.
        '''
        if not timing_data:
            return []

        changes = timing_data.strip().split(',')
        timing_changes = []

        for change in changes:
            # Ignore empty timing key, value pair.
            if not change:
                continue

            values = change.strip().split('=')
            values = [float(value) for value in values]
            if len(values) > 2:
                values[-1] = bool(values[-1])
            timing_changes.append(values)

        return timing_changes

    def timing_changes_to_df(self) -> pd.DataFrame:
        '''
        Returns a data frame storing all timing changes in the stepchart.

        This function will transform all of the timing changes within the
        stepchart into a data frame, whose rows correspond to a timing change
        and whose columns give the beat at which the change occurs and the
        values describing the change (i.e. the value of a BPM change).

        Returns
        -------
        timing_df : pd.DataFrame
            Records all timing changes that occur in the stepchart.
        '''
        data_frames = []

        # Create data frames for each type of timing change.
        for key in self.timing_data:
            cols = Stepchart.timing_map[key]
            data = self.timing_data[key]
            parsed_data = self.parse_timing_changes(key, data)
            if parsed_data:
                df = pd.DataFrame(columns = cols, data = parsed_data)
                data_frames.append(df)

        # Merge timing data frames.
        timing_df = reduce(
            lambda df1, df2: pd.merge(df1, df2, how='outer', on='beat'),
            data_frames
        )

        # Ensure columns are present regardless of stepchart contents.
        columns = ['stop', 'delay', 'warp']
        for col in columns:
            if col not in timing_df.columns:
                timing_df[col] = np.nan

        # Convert 'speed_mode' column to float.
        timing_df = timing_df.astype({'speed_mode': 'float64'})

        return timing_df

    def steps_to_df(self) -> pd.DataFrame:
        '''
        Returns a data frame storing all steps in the stepchart.

        This function will transform all of the notes within the stepchart into
        a data frame, whose rows correspond to notes and whose columns give the
        beat at which the note occurs and the steps within (meaning which types
        of steps occur at each panel).

        Returns
        -------
        steps_df : pd.DataFrame
            Records all steps in the stepchart.
        '''
        parsed_stepchart = self.parse_steps(self.notes)
        steps_cols = ['panel', 'step_type', 'beat']
        steps_df = pd.DataFrame(columns = steps_cols, data = parsed_stepchart)

        return steps_df

    def chart_to_df(self) -> pd.DataFrame:
        '''
        Returns a data frame storing all step and timing changes.

        This function combines the data frames produced by the timing change
        and step data frames produced by the steps_to_df and
        timing_changes_to_df methods into a single data frame describing the
        stepchart. The rows correspond to "events" (notes/timing changes) within
        the stepchart and the columns describe each event as well as the beat
        and second at whcih it occur.
        
        Returns
        -------
        chart_df : pd.DataFrame
            A DataFrame containing all stepchart information, including the
            timing and panels of all tap and hold notes, BPM changes, and
            scroll rate effects.
        '''
        # Merge step and timing data.
        steps_df = self.steps_to_df()
        timing_df = self.timing_changes_to_df()
        df = pd.merge(steps_df, timing_df, on='beat', how='outer')

        # Get rows and columns corresponding to tap notes.
        tap_sel = df['step_type'] == 'tap'
        tap_df = df.loc[tap_sel, ['beat', 'panel']]

        # Get rows corresponding to hold notes.
        hold_caps = df['step_type'] == 'hold (cap)'
        hold_tails = df['step_type'] == 'hold (tail)'
        hold_sel = (hold_caps) | (hold_tails)
        hold_cols = ['panel', 'step_type', 'beat']
        sort_cols = ['panel', 'beat', 'step_type']
        hold_df = df.loc[hold_sel, hold_cols].sort_values(sort_cols)

        # Fix holds that are warped over.
        warps = df.loc[df['warp'] > 0, ['beat', 'warp']].copy()
        warps['end'] = warps['beat'] + warps['warp']
        cap_warped = lambda x: warps.loc[
            (warps['beat'] < x) & (warps['end'] > x),
            'end'
        ].max()
        sel = hold_df['step_type'] == 'hold (cap)'
        caps = hold_df.loc[sel, 'beat']
        fixed_caps = caps.apply(cap_warped).fillna(caps)
        hold_df.loc[sel, 'beat'] = fixed_caps
        tail_warped = lambda x: warps.loc[
            (warps['beat'] < x) & (warps['end'] > x),
            'beat'
        ].max()
        sel = hold_df['step_type'] == 'hold (tail)'
        tails = hold_df.loc[sel, 'beat']
        fixed_tails = tails.apply(tail_warped).fillna(tails)
        hold_df.loc[sel, 'beat'] = fixed_tails

        # Get hold duration.
        hold_df['duration'] = hold_df['beat'].diff(-1).abs()
        cap_sel = hold_df['step_type'] == 'hold (cap)'
        tail_sel = hold_df['step_type'] == 'hold (tail)'
        hold_df.loc[tail_sel, 'duration'] = 0

        hold_df = hold_df.drop('step_type', axis=1)

        # Get string representing the possible panels.
        if self.panels == 5:
            panels = 'ZQSEC'
        elif self.panels == 10:
            panels = 'ZQSECVRGYN'
        else:
            panels = ''

        # Dummify panel columns.
        for panel in panels:
            panel_sel = tap_df['panel'] == panel
            tap_df[f'tap_{panel}'] = panel_sel
            panel_sel = hold_df['panel'] == panel
            hold_df[f'hold_{panel}'] = panel_sel & cap_sel
            hold_df[f'hold_duration_{panel}'] = panel_sel * hold_df['duration']

        # Drop artifact columns and merge rows with equal beats.
        hold_df = hold_df.drop(['panel','duration'], axis=1)
        hold_df = hold_df.groupby('beat').sum().reset_index()
        tap_df = tap_df.drop('panel', axis=1)
        tap_df = tap_df.groupby('beat').sum().reset_index()

        # Set hold durations to null when no hold is active.
        for panel in panels:
            panel_sel = df['panel'] == panel
            cap_sel = df['step_type'] == 'hold (cap)'
            tail_sel = df['step_type'] == 'hold (tail)'
            sel = panel_sel & (cap_sel | tail_sel)
            beats = df.loc[sel, 'beat']
            inactive_beats = ~hold_df['beat'].isin(beats)
            col = f'hold_duration_{panel}'
            hold_df.loc[inactive_beats, col] = np.nan

        # Get tickcounts.
        sel = df['tickcount'].notna()
        tickcount_df = df.loc[sel, ['beat', 'tickcount']].copy()

        # Get columns corresponding to real time data.
        timing_cols = ['beat', 'bpm', 'stop', 'delay', 'warp']
        sel = reduce(
            lambda s1, s2: s1 | s2,
            (df[col].notna() for col in timing_cols[1:])
        )
        timing_df = df.loc[sel, timing_cols]

        # Get columns corresponding to scroll rate changes.
        scroll_cols = [
            'beat',
            'speed',
            'speed_duration',
            'speed_mode',
            'scroll_factor'
        ]
        sel = reduce(
            lambda s1, s2: s1 | s2,
            (df[col].notna() for col in scroll_cols[1:])
        )
        scroll_df = df.loc[sel, scroll_cols]

        # Merge data frames and sort by beat.
        data_frames = [tap_df, hold_df, tickcount_df, timing_df, scroll_df]
        chart_df = reduce(
            lambda df1, df2: pd.merge(df1, df2, how='outer', on='beat'),
            data_frames
        ).drop_duplicates().sort_values('beat')

        # Fill in hold durations.
        cols = [f'hold_duration_{panel}' for panel in panels]
        for col in cols:
            tail_beat = chart_df[col].where(
                chart_df[col].isna(),
                chart_df['beat'] + chart_df[col]
            ).ffill()
            duration = chart_df[col].fillna(tail_beat - chart_df['beat'])
            chart_df[col] = duration
            chart_df[col] = np.where(duration >= 0, duration, np.nan)

        # Rows and columns correspoding to warps.
        warps = chart_df.loc[chart_df['warp'] > 0, ['beat', 'warp']].copy()
        warps['end'] = warps['beat'] + warps['warp']

        # Ignore steps placed on top of warps.
        step_cols = []
        for panel in panels:
            cols = [f'tap_{panel}', f'hold_{panel}']
            step_cols.extend(cols)
        chart_df.loc[warps.index, step_cols] = 0

        # Drop rows which are warped over.
        warped = lambda x: ((x > warps['beat']) & (x < warps['end'])).sum() > 0
        warped_over = chart_df['beat'].apply(warped)
        warped_over = chart_df.loc[warped_over, :]
        chart_df = chart_df.drop(warped_over.index)

        # Forward fill bpm and 0-fill other columns.
        chart_df['bpm'] = chart_df['bpm'].ffill()
        cols = ['stop', 'delay', 'warp']
        chart_df.loc[:, cols] = chart_df.loc[:, cols].fillna(0)

        # Get row-to-row changes in beats and combine with stop, delay, and
        # warp numbers to get elapsed seconds for each row.
        warp_sum = chart_df['warp'].cumsum().shift(1).fillna(0)
        beats_corrected = chart_df['beat'] - warp_sum
        beat_delta = beats_corrected.diff(-1).fillna(0).abs()
        spb = 60 / chart_df['bpm'] # seconds per beat
        time_shift = (chart_df['stop'] + chart_df['delay']).cumsum()
        time_shift -= self.offset
        sec = (beat_delta * spb).cumsum() + time_shift
        sec = sec.shift(1).fillna(0)
        chart_df['sec'] = sec
        
        # Forward fill speed and scroll factor and create scroll rate column.
        chart_df['speed'] = chart_df['speed'].ffill()
        chart_df['scroll_factor'] = chart_df['scroll_factor'].ffill()
        scroll_rate = chart_df['speed'] * chart_df['scroll_factor']
        chart_df['scroll_rate'] = scroll_rate

        # Convert dummy columns to ints.
        for panel in panels:
            cols = [f'tap_{panel}', f'hold_{panel}']
            for col in cols:
                chart_df[col] = chart_df[col].fillna(0).astype(int)

        # Reorder columns and reset_index
        cols_ordered = ['beat', 'sec', 'bpm']
        tap_cols = [f'tap_{panel}' for panel in panels]
        hold_cols = [f'hold_{panel}' for panel in panels]
        hold_duration_cols = [f'hold_duration_{panel}' for panel in panels]
        cols_ordered.extend(tap_cols + hold_cols + hold_duration_cols)
        cols_ordered.append('tickcount')
        cols_ordered.extend(timing_cols[2:] + scroll_cols[1:])
        chart_df = chart_df.loc[:, cols_ordered].reset_index(drop=True)

        # Correct initial time.
        chart_df.loc[0, 'sec'] = -self.offset

        # Forward fill tickcount column.
        chart_df['tickcount'] = chart_df['tickcount'].ffill()

        return chart_df