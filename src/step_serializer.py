'''
This module contains the StepSerializer class, which can be used to serialize
the steps of a Pump It Up stepchart.
'''

import pandas as pd, numpy as np

class StepSerializer:
    '''
    This class serializes a Pump It Up stepchart.

    The serialized chart contains steps that occur and the relevant timestamps
    (in seconds).
    '''
    panels = {
        'S': ['Z', 'Q', 'S', 'E', 'C'],
        'D': ['Z', 'Q', 'S', 'E', 'C', 'V', 'R', 'G', 'Y', 'N']
    }
    tap_cols = {
        'S': [f'tap_{panel}' for panel in panels['S']],
        'D': [f'tap_{panel}' for panel in panels['D']]
    }
    hold_cols = {
        'S': [f'hold_{panel}' for panel in panels['S']],
        'D': [f'hold_{panel}' for panel in panels['D']]
    }
    hold_dur_cols = {
        'S': [f'hold_duration_{panel}' for panel in panels['S']],
        'D': [f'hold_duration_{panel}' for panel in panels['D']]
    }

    def serialize_steps(self, step_type: str, chart_df: pd.DataFrame) -> str:
        '''
        Serializes the steps of a stepchart.

        The output consists of items separated by hyphens. Each item consists
        of two subitems, separated by a colon - a timestamp (the second at
        which the note occurs), and the steps. The steps are encoded using the
        convention that the characters ZQSEC correspond to the panels on the P1
        pad, while the characters VRGYN correspond to the panels on the P2 pad.
        An uppercase letter indicates a tap, while a lowercase letter indicates
        a hold. A lowercase letter followed by a 1 indicates the cap of a hold,
        while a lowercase letter followed by a 0 indicates the tail of a hold.

        Parameters
        ----------
        step_type : str
            Equal to 'S' if the chart is a singles chart or 'D' if the chart is
            a doubles chart.
        chart_df : pd.DataFrame
            A data frame representing a step chart produced by the get_chart
            method of the StepchartParser class.

        Returns
        -------
        steps: str
            A string containing hypen-separated components which indicate a
            step together with the time at which it occurs.
        '''
        # Isolate tap notes and hold caps/tails.
        taps = chart_df.loc[:, self.tap_cols[step_type]].sum(axis=1)
        hold_caps = chart_df.loc[:, self.hold_cols[step_type]].sum(axis=1)
        hold_tails = chart_df.loc[:, self.hold_dur_cols[step_type]] == 0
        sel = (taps > 0) | (hold_caps > 0) | hold_tails.any(axis=1)
        cols = ['sec'] + self.tap_cols[step_type] + self.hold_cols[step_type] \
            + self.hold_dur_cols[step_type]
        df = chart_df.loc[sel, cols]

        # Convert step columns to strings.
        taps = df.loc[:, self.tap_cols[step_type]].apply(
            lambda col: np.char.multiply(
                col.name.split('_')[-1],
                col.astype(int)
            )
        )
        hold_caps = df.loc[:, self.hold_cols[step_type]].apply(
            lambda col: np.char.multiply(
                f'{col.name.split("_")[-1].lower()}1',
                col.astype(int)
            )
        )
        hold_interiors = df.loc[:, self.hold_dur_cols[step_type]].apply(
            lambda col: np.char.multiply(
                col.name.split('_')[-1].lower(),
                ((col > 0) * (df[f'hold_{col.name[-1]}'] == 0)).astype(int)
            )
        )
        hold_tails = df.loc[:, self.hold_dur_cols[step_type]].apply(
            lambda col: np.char.multiply(
                f'{col.name.split("_")[-1].lower()}0',
                (col == 0).astype(int)
            )
        )

        # Merge columns
        string_df = pd.concat([
            np.round(df['sec'], 3).astype(str) + ':',
            taps,
            hold_caps,
            hold_interiors + hold_tails
        ], axis=1)

        # Get string representation of steps.
        steps = '-'.join(string_df.sum(axis=1))

        return steps