"""Interactive plots of coverage and sampling sites for harmonized data.

Run the cells in a Python/Jupyter environment.  Edit ``INPUT_DIR`` in the
final cell if the data directory is elsewhere.  This file does not parse
command-line arguments or write plot files.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd


VARIABLES = {
    # Blue, vermilion, and magenta remain distinct over green satellite imagery.
    "volumetric_water_content_m3_m3": ("Volumetric water content", "#0072B2"),
    "gravimetric_water_content_gH2O_gs": ("Gravimetric water content", "#D55E00"),
    "water_potential_kPa": ("Water potential", "#CC79A7"),
}
MARKERS = {True: "o", False: "s"}


def dataset_id_from_path(path: Path) -> str:
    """Return the ID used in the location crosswalk from an output file name."""
    return path.name.removesuffix("_harmonized.csv")


def read_measurements(input_dir: Path) -> pd.DataFrame:
    """Read every measurement output and add its source dataset identifier."""
    files = sorted(
        path
        for path in input_dir.glob("*_harmonized.csv")
        if path.name != "location_data_harmonized_with_uuid.csv"
    )
    if not files:
        raise FileNotFoundError(f"No *_harmonized.csv measurement files found in {input_dir}")

    required = {"datetime_UTC", "site_id", "is_timeseries", *VARIABLES}
    tables = []
    for path in files:
        table = pd.read_csv(path)
        missing = required - set(table.columns)
        if missing:
            warnings.warn(f"Skipping {path.name}; missing columns: {sorted(missing)}")
            continue
        table["source_dataset_id"] = dataset_id_from_path(path)
        tables.append(table)
    if not tables:
        raise ValueError("None of the measurement files had the required harmonized columns.")
    return pd.concat(tables, ignore_index=True)


def normalize_boolean(values: pd.Series) -> pd.Series:
    """Normalize booleans read as either Python booleans or CSV strings."""
    return values.astype(str).str.strip().str.lower().map({"true": True, "false": False})


def to_long_measurements(measurements: pd.DataFrame) -> pd.DataFrame:
    """Keep real observations and express their variable type in one column."""
    data = measurements.copy()
    data["datetime_UTC"] = pd.to_datetime(data["datetime_UTC"], utc=True, errors="coerce")
    data["is_timeseries"] = normalize_boolean(data["is_timeseries"])
    # Building only the non-null variable frames avoids making a temporary
    # three-times-larger melt table for this multi-million-row collection.
    identifiers = ["source_dataset_id", "site_id", "datetime_UTC", "is_timeseries"]
    variable_frames = []
    for variable in VARIABLES:
        values = pd.to_numeric(data[variable], errors="coerce")
        valid = data[identifiers].copy()
        valid["value"] = values
        valid = valid.dropna(subset=["site_id", "datetime_UTC", "is_timeseries", "value"])
        valid["variable"] = variable
        variable_frames.append(valid)
    long = pd.concat(variable_frames, ignore_index=True)
    long["site_label"] = (
        long["source_dataset_id"].str.replace("ess-dive-", "", regex=False).str.slice(0, 8)
        + ": "
        + long["site_id"].astype(str)
    )
    return long


def contiguous_intervals(times: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Merge nearby observations into coverage intervals.

    A gap larger than three times the median sampling interval starts a new bar.
    This retains outages while making dense time series readable.
    """
    stamps = pd.Series(times.dropna().unique()).sort_values().reset_index(drop=True)
    if stamps.empty:
        return []
    if len(stamps) == 1:
        return [(stamps.iloc[0], stamps.iloc[0] + pd.Timedelta(days=1))]
    gaps = stamps.diff().dropna()
    positive_gaps = gaps[gaps > pd.Timedelta(0)]
    median_gap = positive_gaps.median() if not positive_gaps.empty else pd.Timedelta(days=1)
    split_after = gaps > 3 * median_gap
    starts = [0, *list(np.flatnonzero(split_after.to_numpy()) + 1)]
    ends = [*list(np.flatnonzero(split_after.to_numpy())), len(stamps) - 1]
    # Give an instantaneous campaign observation a visible, one-day-wide bar.
    return [
        (stamps.iloc[start], max(stamps.iloc[end], stamps.iloc[start] + pd.Timedelta(days=1)))
        for start, end in zip(starts, ends)
    ]


def plot_availability(long: pd.DataFrame):
    """Create a Gantt-style coverage plot, grouped by source-aware site identifier."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Sensor depths and replicates share observation times.  One timestamp per
    # site/variable/record-type is enough to communicate availability.
    coverage = long.drop_duplicates(
        ["site_label", "variable", "is_timeseries", "datetime_UTC"]
    )
    coverage = coverage.loc[coverage["is_timeseries"].eq(True)]
    if coverage.empty:
        raise ValueError("No time-series observations are available for the coverage plot.")
    site_order = (
        coverage.groupby("site_label")["datetime_UTC"].min().sort_values().index.tolist()
    )
    height = max(7, min(0.22 * len(site_order) + 2.5, 60))
    fig, ax = plt.subplots(figsize=(15, height), constrained_layout=True)
    offsets = np.linspace(-0.28, 0.28, len(VARIABLES))
    site_positions = {site: position for position, site in enumerate(site_order)}
    variable_offsets = dict(zip(VARIABLES, offsets))
    for (site, variable, _is_timeseries), subset in coverage.groupby(
        ["site_label", "variable", "is_timeseries"], sort=False
    ):
        for start, end in contiguous_intervals(subset["datetime_UTC"]):
            ax.barh(
                site_positions[site] + variable_offsets[variable],
                (end - start).total_seconds() / 86400,
                left=mdates.date2num(start),
                height=0.22,
                color=VARIABLES[variable][1],
                edgecolor="none",
            )
    ax.set_yticks(range(len(site_order)), site_order, fontsize=6)
    ax.invert_yaxis()
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_xlabel("Observation date (UTC)")
    ax.set_ylabel("Source dataset: site identifier")
    ax.set_title("Data availability and continuity by sampling site")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(
        handles=[Patch(color=color, label=name) for name, color in VARIABLES.values()],
        title="Variable type",
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
    )
    plt.show()
    return fig


def plot_map(long: pd.DataFrame, locations_path: Path, is_timeseries: bool):
    """Plot one record type's variable-colored sites on satellite imagery."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    locations = pd.read_csv(locations_path)
    location_columns = {"source_dataset_id", "site_id", "latitude", "longitude"}
    missing = location_columns - set(locations.columns)
    if missing:
        raise ValueError(f"Location crosswalk is missing columns: {sorted(missing)}")
    locations = locations[list(location_columns)].copy()
    locations["latitude"] = pd.to_numeric(locations["latitude"], errors="coerce")
    locations["longitude"] = pd.to_numeric(locations["longitude"], errors="coerce")
    points = long.drop_duplicates(
        ["source_dataset_id", "site_id", "variable", "is_timeseries"]
    ).merge(locations, on=["source_dataset_id", "site_id"], how="left")
    points = points.loc[points["is_timeseries"].eq(is_timeseries)]
    points = points.dropna(subset=["latitude", "longitude"]).drop_duplicates(
        ["source_dataset_id", "site_id", "variable", "is_timeseries", "latitude", "longitude"]
    )
    if points.empty:
        raise ValueError("No observations could be matched to valid latitude/longitude values.")

    # Web Mercator coordinates permit contextily to overlay a tiled satellite image.
    lon = points["longitude"].to_numpy()
    lat = points["latitude"].clip(-85.05112878, 85.05112878).to_numpy()
    points["x"] = np.deg2rad(lon) * 6378137.0
    points["y"] = 6378137.0 * np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))

    fig, ax = plt.subplots(figsize=(12, 10), constrained_layout=True)
    marker = MARKERS[is_timeseries]
    for variable, (_, color) in VARIABLES.items():
        subset = points[points["variable"] == variable]
        if not subset.empty:
            ax.scatter(
                subset["x"], subset["y"], s=68, marker=marker, c=color,
                edgecolors="black", linewidths=0.9, alpha=0.98, zorder=2,
            )
    x_pad = max((points["x"].max() - points["x"].min()) * 0.08, 1_000)
    y_pad = max((points["y"].max() - points["y"].min()) * 0.08, 1_000)
    ax.set_xlim(points["x"].min() - x_pad, points["x"].max() + x_pad)
    ax.set_ylim(points["y"].min() - y_pad, points["y"].max() + y_pad)
    try:
        import contextily as cx

        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution_size=6)
    except (ImportError, OSError, RuntimeError) as error:
        warnings.warn(f"Satellite basemap unavailable ({error}); displaying point-only map.")
        ax.set_facecolor("#edf3f5")
        ax.grid(alpha=0.3)
    ax.set_axis_off()
    ax.set_title(f"Sampling sites (is_timeseries = {is_timeseries})")
    variable_handles = [
        Line2D([0], [0], marker=marker, color="none", markerfacecolor=color,
               markeredgecolor="black", markersize=8, label=name)
        for name, color in VARIABLES.values()
    ]
    ax.legend(handles=variable_handles, title="Variable type", loc="upper left")
    plt.show()
    return fig


def show_harmonized_data_coverage(input_dir: Path):
    """Load data and display coverage plus one map for each record type."""
    measurements = read_measurements(input_dir)
    long = to_long_measurements(measurements)
    if long.empty:
        raise ValueError("No non-null observations were found in the harmonized files.")
    availability_figure = plot_availability(long)
    locations_path = input_dir / "location_data_harmonized_with_uuid.csv"
    timeseries_map_figure = plot_map(long, locations_path, is_timeseries=True)
    non_timeseries_map_figure = plot_map(long, locations_path, is_timeseries=False)
    return availability_figure, timeseries_map_figure, non_timeseries_map_figure


# %% Run this cell in Jupyter/Positron
INPUT_DIR = Path("./data/processed/harmonized_output_local")
availability_figure, timeseries_map_figure, non_timeseries_map_figure = (
    show_harmonized_data_coverage(INPUT_DIR)
)
