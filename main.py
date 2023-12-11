import pandas as pd
import numpy as np
import plotly.express as px
import re
import time
from functools import wraps
from os import listdir
from os.path import isfile, join
import os
import matplotlib.pyplot as plt

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def read_data_file(directory_files: list) -> pd.DataFrame:
    all_lines = []
    for file_path in directory_files:
        with open(file_path, 'r') as f:
            raw_file = f.readlines()

        list_dados = [line.split() for line in raw_file]
        float_raw_lines = [list(map(float, raw_line)) for raw_line in list_dados]
        all_lines = all_lines + float_raw_lines

    return pd.DataFrame(all_lines, columns=['lat', 'long', 'data_value'])


def read_contour_file(file_path: str) -> pd.DataFrame:
    line_split_comp = re.compile(r'\s*,')

    with open(file_path, 'r') as f:
        raw_file = f.readlines()

    l_raw_lines = [line_split_comp.split(raw_file_line.strip()) for raw_file_line in raw_file]
    l_raw_lines = list(filter(lambda item: bool(item[0]), l_raw_lines))
    float_raw_lines = [list(map(float, raw_line))[:2] for raw_line in l_raw_lines]
    header_line = float_raw_lines.pop(0)
    assert len(float_raw_lines) == int(header_line[0])
    return pd.DataFrame(float_raw_lines, columns=['lat', 'long'])


def calculate_precipition_by_point(lat_check: float, long_check: float, df_precip: pd.DataFrame,
                                   tolerance_area: float = 0.1) -> float:
    condiction1 = df_precip['lat'] >= lat_check - tolerance_area
    condiction2 = df_precip['lat'] <= lat_check + tolerance_area

    condiction3 = df_precip['long'] >= long_check - tolerance_area
    condiction4 = df_precip['long'] <= long_check + tolerance_area

    df_filter = df_precip[condiction1 & condiction2 & condiction3 & condiction4]
    if len(df_filter) > 0:
        return df_filter['acum_value'].mean()
    else:
        return 0


def apply_contour(contour_df: pd.DataFrame, df_all_points: pd.DataFrame) -> pd.DataFrame:
    pass


def main() -> None:
    main_path = os.getcwd() + "\\btg-energy-challenge"
    contour_df: pd.DataFrame = read_contour_file(main_path + '\\PSATCMG_CAMARGOS.bln')

    main_path_forecast = os.getcwd() + "\\btg-energy-challenge\\forecast_files"
    files_in_path = [f for f in listdir(main_path_forecast) if isfile(join(main_path_forecast, f))]
    files_in_path = [main_path_forecast + "\\" + filename for filename in files_in_path]
    data_df: pd.DataFrame = read_data_file(files_in_path)

    # acumulated precipitation
    data_df_acum = data_df.groupby(['lat', 'long']).agg(acum_value=('data_value', 'sum')).reset_index()

    # create points inside contour
    range_lat = [contour_df['lat'].min(), contour_df['lat'].max()]
    range_long = [contour_df['long'].min(), contour_df['long'].max()]
    points_range_lat = np.arange(range_lat[0], range_lat[1], 0.01)
    points_range_long = np.arange(range_long[0], range_long[1], 0.01)
    df_lat = pd.DataFrame({'all_lat': points_range_lat})
    df_long = pd.DataFrame({'all_long': points_range_long})
    df_all_lat_long = df_lat.merge(df_long, how='cross')

    selected_area = Polygon(contour_df.values)
    # polygon = Polygon(tuple(x) for x in contour_df[['lat','long']].to_numpy())

    # check if data is inside contour
    df_all_lat_long['is_contour'] = df_all_lat_long.apply(
        lambda x: selected_area.contains(Point(x['all_lat'], x['all_long'])), axis=1)
    df_all_lat_long['is_contour'] = df_all_lat_long['is_contour'].astype(int)

    # calculate precipition inside contour
    df_all_lat_long['acum_precipition'] = 0
    df_all_lat_long['acum_precipition'] = np.where(df_all_lat_long['is_contour'] == 0, 0, df_all_lat_long.apply(
        lambda x: calculate_precipition_by_point(x['all_lat'], x['all_long'], data_df_acum, tolerance_area=0.25),
        axis=1))

    print('Precipition in selected region:\n',
          df_all_lat_long[df_all_lat_long['is_contour'] == 1]['acum_precipition'].mean())

    df_all_lat_long.plot.scatter(x='all_lat', y='all_long', c='acum_precipition', colormap='Greys',
                                 title='Camargos - Bacia do Grande - Precipitação acumulada',
                                 xlabel='latitude', ylabel='longitude').\
                                get_figure().savefig(main_path + '\\precipition_selected_area.png')


if __name__ == '__main__':
    main()
