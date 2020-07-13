"""Summarize individual evaluations generated by evaluate_models.py

COVID-19 Forecast Hub: https://github.com/reichlab/covid19-forecast-hub
Learn more at: https://github.com/youyanggu/covid19-forecast-hub-evaluation

To see list of command line options: `python summarize_evaluations.py --help`
"""

import argparse
import datetime
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd


def str_to_date(date_str, fmt='%Y-%m-%d'):
    """Convert string date to datetime object."""
    return datetime.datetime.strptime(date_str, fmt).date()


def get_dates_from_fname(fname):
    """Returns the projection and eval date given a file name."""
    basename = os.path.basename(fname).replace('.csv', '')
    try:
        # proj-date_eval-date_eval-type.csv
        proj_date = str_to_date(basename.split('_')[0])
        eval_date = str_to_date(basename.split('_')[1])
    except ValueError:
        # projections_proj-date_eval-date.csv
        proj_date = str_to_date(basename.split('_')[1])
        eval_date = str_to_date(basename.split('_')[2])
    assert eval_date > proj_date

    return proj_date, eval_date


def filter_fnames_by_weeks_ahead(fnames, weeks_ahead):
    """Return evaluation files that match the provided weeks_ahead."""
    include_fnames = []
    for fname in fnames:
        proj_date, eval_date = get_dates_from_fname(fname)

        days_ahead = (eval_date - proj_date).days
        max_days_tolerance = 3
        if abs(days_ahead - 7*weeks_ahead) <= max_days_tolerance:
            # this is a weeks_ahead forecast
            include_fnames.append(fname)

    return include_fnames


def main(eval_date, weeks_ahead, evaluations_dir, out_dir):
    """We combine various evaluations based on either evaluation date or weeks ahead.

    For full description of methods, refer to:
    https://github.com/youyanggu/covid19-forecast-hub-evaluation
    """
    print('Evaluation date:', eval_date)
    print('Weeks ahead:', weeks_ahead)
    print('Evaluations dir:', evaluations_dir)
    print('Output dir:', out_dir)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    assert eval_date or weeks_ahead, \
        'must provide either an --eval_date or --weeks_ahead'
    assert not (eval_date and weeks_ahead), \
        'must provide only one of --eval_date or --weeks_ahead'

    print('==============================')
    print('US evaluations')
    print('==============================')
    if eval_date:
        us_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/{eval_date}/*_{eval_date}_us_errs.csv'))
    else:
        us_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/*/*_us_errs.csv'))
        us_errs_fnames = filter_fnames_by_weeks_ahead(us_errs_fnames, weeks_ahead)

    assert len(us_errs_fnames) > 0, 'Need US evaluation files'

    col_to_data_us = {}
    for us_errs_fname in us_errs_fnames:
        proj_date_, eval_date_ = get_dates_from_fname(us_errs_fname)
        df_us = pd.read_csv(us_errs_fname, index_col=0)
        df_us['perc_error'] = df_us['perc_error'].str.rstrip('%').astype('float') / 100

        col_to_data_us[f'perc_error_{proj_date_}_{eval_date_}'] = df_us['perc_error']

    df_all_us = pd.DataFrame(col_to_data_us)
    df_all_us = df_all_us.dropna(how='all')
    df_all_us = df_all_us.reindex(sorted(df_all_us.columns), axis=1)

    # we sort the models based on their mean rank
    # models with a missing forecast for that week is assigned the max rank
    max_rank_us = df_all_us.abs().rank().max()+1
    cols_for_ranking_us = [c for c in df_all_us.columns if 'perc_error' in c]
    if weeks_ahead:
        cols_for_ranking_us_ = cols_for_ranking_us[:]
    else:
        # only consider projections from past 6 weeks for ranking by eval_date
        cols_for_ranking_us_ = cols_for_ranking_us[-6:]
    df_all_us = df_all_us.reindex(df_all_us.abs().rank().fillna(
        max_rank_us)[cols_for_ranking_us_].mean(axis=1).sort_values().index)

    print('------------------------')
    print('US errors:')
    print(df_all_us[cols_for_ranking_us])
    print('US rankings:')
    print(df_all_us[cols_for_ranking_us].abs().rank())

    if out_dir:
        if eval_date:
            out_fname_us = f'{out_dir}/summary_us_{eval_date}.csv'
        else:
            out_fname_us = f'{out_dir}/summary_{weeks_ahead}_weeks_ahead_us.csv'
        df_all_us.to_csv(out_fname_us, float_format='%.3f')
        print('Saved US summary to:', out_fname_us)

    print('==============================')
    print('State-by-state evaluations')
    print('==============================')
    if eval_date:
        states_abs_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/{eval_date}/*_{eval_date}_states_abs_errs.csv'))
        states_sq_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/{eval_date}/*_{eval_date}_states_sq_errs.csv'))
    else:
        states_abs_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/*/*_states_abs_errs.csv'))
        states_abs_errs_fnames = filter_fnames_by_weeks_ahead(states_abs_errs_fnames, weeks_ahead)
        states_sq_errs_fnames = sorted(glob.glob(
            f'{evaluations_dir}/*/*_states_sq_errs.csv'))
        states_sq_errs_fnames = filter_fnames_by_weeks_ahead(states_sq_errs_fnames, weeks_ahead)

    assert len(states_abs_errs_fnames) > 0, 'Need state-by-state evaluation files'
    assert len(states_sq_errs_fnames) > 0, 'Need state-by-state evaluation files'

    col_to_data_states = {}

    for states_abs_errs_fname in states_abs_errs_fnames:
        proj_date_, eval_date_ = get_dates_from_fname(states_abs_errs_fname)
        df_states = pd.read_csv(states_abs_errs_fname, index_col=0)
        col_to_data_states[f'mean_abs_error_{proj_date_}_{eval_date_}'] = df_states['mean']

    for states_sq_errs_fname in states_sq_errs_fnames:
        proj_date_, eval_date_ = get_dates_from_fname(states_sq_errs_fname)
        df_states = pd.read_csv(states_sq_errs_fname, index_col=0)
        col_to_data_states[f'mean_sq_abs_error_{proj_date_}_{eval_date_}'] = df_states['mean']

    df_all_states = pd.DataFrame(col_to_data_states)
    df_all_states = df_all_states.dropna(how='all')
    df_all_states = df_all_states.reindex(sorted(df_all_states.columns), axis=1)

    # we sort the models based on their mean rank
    # models with a missing forecast for that week is assigned the max rank
    max_ranks_states = df_all_states.abs().rank().max()+1
    cols_for_ranking_states = [c for c in df_all_states.columns if 'mean_abs_error' in c]
    if weeks_ahead:
        cols_for_ranking_states_ = cols_for_ranking_states[:]
    else:
        # only consider projections from past 6 weeks for ranking by eval_date
        cols_for_ranking_states_ = cols_for_ranking_states[-6:]
    df_all_states = df_all_states.reindex(df_all_states.abs().rank().fillna(
        max_ranks_states)[cols_for_ranking_states_].mean(axis=1).sort_values().index)

    print('------------------------')
    print('State-by-state errors:')
    print(df_all_states[cols_for_ranking_states])
    print('State-by-state rankings:')
    print(df_all_states[cols_for_ranking_states].abs().rank())

    if out_dir:
        if eval_date:
            out_fname_states = f'{out_dir}/summary_states_{eval_date}.csv'
        else:
            out_fname_states = f'{out_dir}/summary_{weeks_ahead}_weeks_ahead_states.csv'
        df_all_states.to_csv(out_fname_states, float_format='%.1f')
        print('Saved states summary to:', out_fname_states)

    print('==============================')
    print('Baseline evaluations')
    print('==============================')
    if eval_date:
        projections_fnames = sorted(glob.glob(
            f'{evaluations_dir}/{eval_date}/projections_*_{eval_date}.csv'))
    else:
        projections_fnames = sorted(glob.glob(
            f'{evaluations_dir}/*/projections_*.csv'))
        projections_fnames = filter_fnames_by_weeks_ahead(projections_fnames, weeks_ahead)

    assert len(projections_fnames) > 0, 'Need state-by-state projection files'

    col_to_data = {}
    for projections_fname in projections_fnames:
        proj_date_, eval_date_ = get_dates_from_fname(projections_fname)
        df_states = pd.read_csv(projections_fname, index_col=0)

        df_states = df_states[df_states.index != 'US']

        model_names = ['Baseline'] + [c for c in df_states.columns if \
            ('-' in c and 'error-' not in c and 'beat_baseline-' not in c)]

        num_states = len(df_states)
        col_data = {
            'num_states' : num_states,
        }
        df_states_num_projections = (~pd.isnull(df_states)).sum()
        df_states_sum = df_states.abs().sum(min_count=1)
        for model_name in model_names:
            num_with_projections = df_states_num_projections.loc[model_name]
            if model_name != 'Baseline':
                num_beat_baseline = df_states_sum.loc[f'beat_baseline-{model_name}']

                col_data[f'num_states_with_projections-{model_name}'] = num_with_projections
                if pd.isnull(num_beat_baseline):
                    col_data[f'num_states_beat_baseline-{model_name}'] = np.nan
                    col_data[f'perc_beat_baseline-{model_name}'] = np.nan
                else:
                    col_data[f'num_states_beat_baseline-{model_name}'] = int(num_beat_baseline)
                    col_data[f'perc_beat_baseline-{model_name}'] = num_beat_baseline / num_with_projections

            if num_with_projections == num_states:
                # Only calculate mean abs error if there are projections for every state
                col_data[f'mean_abs_error-{model_name}'] = df_states_sum.loc[f'error-{model_name}'] / num_states
            else:
                col_data[f'mean_abs_error-{model_name}'] = np.nan

        col_to_data[f'{proj_date_}_{eval_date_}'] = col_data

    df_all = pd.DataFrame(col_to_data)
    row_ordering = ['num_states'] + \
        sorted([c for c in df_all.index if 'num_states_with_projections' in c]) + \
        sorted([c for c in df_all.index if 'num_states_beat_baseline' in c]) + \
        sorted([c for c in df_all.index if 'perc_beat_baseline' in c]) + \
        sorted([c for c in df_all.index if 'mean_abs_error' in c])
    df_all = df_all.loc[row_ordering]

    if out_dir:
        os.makedirs(f'{out_dir}/baseline_comparison', exist_ok=True)
        if eval_date:
            out_fname = f'{out_dir}/baseline_comparison/baseline_comparison_states_{eval_date}.csv'
        else:
            out_fname = f'{out_dir}/baseline_comparison/baseline_comparison_{weeks_ahead}_weeks_ahead_states.csv'
        df_all.to_csv(out_fname, float_format='%.10g')
        print('Saved global summary to:', out_fname)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Given an evaluation date or weeks ahead (not both),'
            'summarize all the historical projections that fit the criteria.'))
    parser.add_argument('--eval_date',
        help='Evaluate all projections based on eval_date')
    parser.add_argument('--weeks_ahead', type=int,
        help='Evaluate all projections based on number of weeks ahead.')
    parser.add_argument('--evaluations_dir',
        help='Directory containing the raw evaluations.')
    parser.add_argument('--out_dir',
        help='Directory to save output data.')

    args = parser.parse_args()
    eval_date = args.eval_date
    weeks_ahead = args.weeks_ahead
    evaluations_dir = args.evaluations_dir
    out_dir = args.out_dir

    if eval_date:
        eval_date = str_to_date(args.eval_date)
    if not evaluations_dir:
        evaluations_dir = Path(__file__).parent / 'evaluations'

    main(eval_date, weeks_ahead, evaluations_dir, out_dir)
    print('Done', datetime.datetime.now())

