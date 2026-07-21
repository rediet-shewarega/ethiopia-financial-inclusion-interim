from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Ethiopia Financial Inclusion Forecast",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1350px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 14px;
            padding: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Ethiopia Financial Inclusion Forecasting Dashboard")


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ENRICHED_PATH = PROCESSED_DIR / "ethiopia_fi_enriched.csv"
IMPACT_PATH = PROCESSED_DIR / "event_impact_link_summary.csv"
ASSOCIATION_PATH = (
    PROCESSED_DIR
    / "event_indicator_association_matrix.csv"
)
FORECAST_PATH = PROCESSED_DIR / "forecasts_2025_2027.csv"


# =========================================================
# DATA LOADING
# =========================================================

def normalize_columns(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Return a copy with consistent column names."""

    result = frame.copy()

    result.columns = (
        result.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    return result


@st.cache_data(show_spinner=False)
def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load and prepare all dashboard datasets."""

    required_files = [
        ENRICHED_PATH,
        IMPACT_PATH,
        ASSOCIATION_PATH,
        FORECAST_PATH,
    ]

    missing_files = [
        file_path
        for file_path in required_files
        if not file_path.exists()
    ]

    if missing_files:
        missing_text = "\n".join(
            f"- {file_path}"
            for file_path in missing_files
        )

        raise FileNotFoundError(
            "Required dashboard files are missing:\n"
            f"{missing_text}"
        )

    enriched = normalize_columns(
        pd.read_csv(ENRICHED_PATH)
    )

    impacts = normalize_columns(
        pd.read_csv(IMPACT_PATH)
    )

    association = pd.read_csv(
        ASSOCIATION_PATH,
        index_col=0,
    )

    forecasts = normalize_columns(
        pd.read_csv(FORECAST_PATH)
    )

    association = association.apply(
        pd.to_numeric,
        errors="coerce",
    ).fillna(0.0)

    for column in [
        "observation_date",
        "event_date",
        "collection_date",
    ]:
        if column in enriched.columns:
            enriched[column] = pd.to_datetime(
                enriched[column],
                errors="coerce",
            )

    if "event_date_resolved" in impacts.columns:
        impacts["event_date_resolved"] = pd.to_datetime(
            impacts["event_date_resolved"],
            errors="coerce",
        )

    numeric_columns = [
        "value_numeric",
        "effect_score",
        "near_term_effect_score",
        "lag_months",
        "year",
        "forecast_percent",
        "lower_90_percent",
        "upper_90_percent",
    ]

    for frame in [
        enriched,
        impacts,
        forecasts,
    ]:
        for column in numeric_columns:
            if column in frame.columns:
                frame[column] = pd.to_numeric(
                    frame[column],
                    errors="coerce",
                )

    return (
        enriched,
        impacts,
        association,
        forecasts,
    )


try:
    (
        enriched_df,
        impact_df,
        association_matrix,
        forecast_df,
    ) = load_data()

except (
    FileNotFoundError,
    pd.errors.ParserError,
) as error:
    st.error(str(error))
    st.stop()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def latest_indicator_row(
    indicator_code: str,
) -> pd.Series | None:
    """Return the latest valid row for an indicator."""

    if "indicator_code" not in enriched_df.columns:
        return None

    rows = enriched_df[
        enriched_df["indicator_code"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .eq(indicator_code.upper())
    ].copy()

    if rows.empty:
        return None

    rows["value_numeric"] = pd.to_numeric(
        rows["value_numeric"],
        errors="coerce",
    )

    rows = rows.dropna(
        subset=["value_numeric"]
    )

    if rows.empty:
        return None

    date_columns = [
        column
        for column in [
            "observation_date",
            "event_date",
            "collection_date",
        ]
        if column in rows.columns
    ]

    if date_columns:
        date_values = pd.concat(
            [
                pd.to_datetime(
                    rows[column],
                    errors="coerce",
                ).rename(column)
                for column in date_columns
            ],
            axis=1,
        )

        rows["_latest_date"] = date_values.max(
            axis=1
        )

        rows = rows.sort_values(
            "_latest_date",
            na_position="first",
        )

    return rows.iloc[-1]


def latest_indicator_value(
    indicator_code: str,
) -> float | None:
    """Return the latest numeric indicator value."""

    row = latest_indicator_row(
        indicator_code
    )

    if row is None:
        return None

    return float(
        row["value_numeric"]
    )


def compact_number(
    value: float | int | None,
) -> str:
    """Format large values using K, M, or B."""

    if value is None or pd.isna(value):
        return "N/A"

    numeric_value = float(value)
    absolute_value = abs(numeric_value)

    if absolute_value >= 1_000_000_000:
        return (
            f"{numeric_value / 1_000_000_000:.1f}B"
        )

    if absolute_value >= 1_000_000:
        return (
            f"{numeric_value / 1_000_000:.1f}M"
        )

    if absolute_value >= 1_000:
        return (
            f"{numeric_value / 1_000:.1f}K"
        )

    return f"{numeric_value:,.1f}"


def format_value_with_unit(
    value: float | int | None,
    unit: object,
) -> str:
    """
    Format values when the source unit already states
    million, billion, or thousand.
    """

    if value is None or pd.isna(value):
        return "N/A"

    numeric_value = float(value)
    unit_text = str(unit).strip().lower()

    if (
        "billion" in unit_text
        and abs(numeric_value) < 1_000_000
    ):
        return f"{numeric_value:,.1f}B"

    if (
        "million" in unit_text
        and abs(numeric_value) < 1_000_000
    ):
        return f"{numeric_value:,.1f}M"

    if (
        "thousand" in unit_text
        and abs(numeric_value) < 1_000_000
    ):
        return f"{numeric_value:,.1f}K"

    return compact_number(
        numeric_value
    )


def download_csv_button(
    frame: pd.DataFrame,
    label: str,
    filename: str,
) -> None:
    """Display a reusable CSV download button."""

    st.download_button(
        label=label,
        data=frame.to_csv(
            index=False
        ).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


# =========================================================
# VALIDATED NATIONAL SERIES
# =========================================================

access_history = pd.DataFrame({
    "year": [
        2011,
        2014,
        2017,
        2021,
        2024,
    ],
    "access_percent": [
        14.0,
        22.0,
        35.0,
        46.0,
        49.0,
    ],
})

usage_baseline = latest_indicator_value(
    "USG_ACTIVE_RATE"
)

if usage_baseline is None:
    usage_baseline = 66.0


crossover_ratio = latest_indicator_value(
    "USG_CROSSOVER"
)

if crossover_ratio is None:
    p2p_value = latest_indicator_value(
        "USG_P2P_COUNT"
    )

    atm_value = latest_indicator_value(
        "USG_ATM_COUNT"
    )

    if (
        p2p_value is not None
        and atm_value not in [
            None,
            0,
        ]
    ):
        crossover_ratio = (
            p2p_value
            / atm_value
        )


baseline_2027 = forecast_df[
    forecast_df["dimension"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    .eq("access")
    & forecast_df["scenario"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    .eq("baseline")
    & forecast_df["year"].eq(2027)
]

baseline_2027_value = (
    float(
        baseline_2027.iloc[0][
            "forecast_percent"
        ]
    )
    if not baseline_2027.empty
    else np.nan
)


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

st.sidebar.title(
    "Financial Inclusion"
)

st.sidebar.caption(
    "Explore Access, Usage, event impacts, "
    "and 2025–2027 forecasts."
)

page = st.sidebar.radio(
    "Dashboard section",
    [
        "Overview",
        "Trends",
        "Event Impacts",
        "Forecasts",
        "Inclusion Projections",
    ],
)

st.sidebar.divider()

st.sidebar.caption(
    "Forecasts are planning scenarios rather "
    "than exact predictions."
)


# =========================================================
# OVERVIEW PAGE
# =========================================================

if page == "Overview":

    st.header("Overview")

    st.write(
        "Current values, historical growth, "
        "and ecosystem indicators."
    )

    (
        metric_column_1,
        metric_column_2,
        metric_column_3,
        metric_column_4,
    ) = st.columns(4)

    metric_column_1.metric(
        label="Account ownership",
        value="49.0%",
        delta="+3.0 pp since 2021",
    )

    metric_column_2.metric(
        label="Mobile money activity",
        value=f"{usage_baseline:.1f}%",
        delta="2024 baseline",
        delta_color="off",
    )

    ratio_text = (
        f"{crossover_ratio:.2f}×"
        if crossover_ratio is not None
        and not pd.isna(crossover_ratio)
        else "N/A"
    )

    metric_column_3.metric(
        label="P2P / ATM crossover",
        value=ratio_text,
        delta="Above 1 means P2P exceeds ATM",
        delta_color="off",
    )

    forecast_text = (
        f"{baseline_2027_value:.1f}%"
        if not pd.isna(
            baseline_2027_value
        )
        else "N/A"
    )

    metric_column_4.metric(
        label="Baseline Access forecast",
        value=forecast_text,
        delta="2027",
        delta_color="off",
    )

    st.subheader(
        "Account ownership trajectory"
    )

    access_figure = px.line(
        access_history,
        x="year",
        y="access_percent",
        markers=True,
        labels={
            "year": "Year",
            "access_percent": (
                "Adults with an account (%)"
            ),
        },
    )

    access_figure.add_hline(
        y=60,
        line_dash="dash",
        annotation_text="60% target",
        annotation_position="top right",
    )

    access_figure.update_traces(
        line_width=3,
        marker_size=8,
    )

    access_figure.update_layout(
        height=450,
        hovermode="x unified",
    )

    st.plotly_chart(
        access_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "responsive": True,
        },
    )

    st.info(
        "Account ownership increased from 14% "
        "in 2011 to 49% in 2024, but growth "
        "slowed to only three percentage points "
        "from 2021 to 2024."
    )

    st.subheader(
        "Latest ecosystem scale indicators"
    )

    indicator_map = {
        "USG_P2P_COUNT": (
            "P2P transactions"
        ),
        "USG_ATM_COUNT": (
            "ATM transactions"
        ),
        "USG_TELEBIRR_USERS": (
            "Telebirr users"
        ),
        "USG_MPESA_USERS": (
            "M-Pesa users"
        ),
        "ACC_TELEBIRR_AGENTS": (
            "Telebirr agents"
        ),
        "USG_TELEBIRR_MERCHANTS": (
            "Telebirr merchants"
        ),
    }

    ecosystem_rows = []

    for code, label in indicator_map.items():
        row = latest_indicator_row(
            code
        )

        if row is None:
            continue

        value = float(
            row["value_numeric"]
        )

        unit = row.get(
            "unit",
            "",
        )

        if value > 0:
            ecosystem_rows.append({
                "indicator": label,
                "indicator_code": code,
                "value": value,
                "unit": unit,
                "display_value": (
                    format_value_with_unit(
                        value,
                        unit,
                    )
                ),
            })

    ecosystem_df = pd.DataFrame(
        ecosystem_rows
    )

    if ecosystem_df.empty:
        st.info(
            "No ecosystem scale indicators "
            "were available."
        )

    else:
        ecosystem_figure = px.bar(
            ecosystem_df.sort_values(
                "value"
            ),
            x="value",
            y="indicator",
            orientation="h",
            text="display_value",
            log_x=True,
            hover_data={
                "indicator_code": True,
                "unit": True,
                "value": ":,.2f",
            },
            labels={
                "value": (
                    "Latest value "
                    "(logarithmic scale)"
                ),
                "indicator": "",
            },
        )

        ecosystem_figure.update_traces(
            textposition="outside"
        )

        ecosystem_figure.update_layout(
            height=430,
            showlegend=False,
        )

        st.plotly_chart(
            ecosystem_figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )

    download_csv_button(
        enriched_df,
        "Download enriched dataset",
        "ethiopia_fi_enriched.csv",
    )


# =========================================================
# CORRECTED TRENDS PAGE
# =========================================================

elif page == "Trends":

    st.header("Interactive Trends")

    st.write(
        "Select indicators and a date range "
        "to explore the available observations."
    )

    observations = enriched_df[
        enriched_df["record_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("observation")
    ].copy()

    observations["value_numeric"] = pd.to_numeric(
        observations["value_numeric"],
        errors="coerce",
    )

    observations["observation_date"] = pd.to_datetime(
        observations["observation_date"],
        errors="coerce",
    )

    observations = observations.dropna(
        subset=[
            "indicator_code",
            "value_numeric",
            "observation_date",
        ]
    ).copy()

    observations["indicator_code"] = (
        observations["indicator_code"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Remove the mixed national and subgroup
    # account-ownership records.
    observations = observations[
        ~observations[
            "indicator_code"
        ].eq("ACC_OWNERSHIP")
    ].copy()

    # Add the validated national series only.
    validated_access_trend = pd.DataFrame({
        "record_type": [
            "observation",
            "observation",
            "observation",
            "observation",
            "observation",
        ],
        "indicator": [
            "Account Ownership",
            "Account Ownership",
            "Account Ownership",
            "Account Ownership",
            "Account Ownership",
        ],
        "indicator_code": [
            "ACC_OWNERSHIP",
            "ACC_OWNERSHIP",
            "ACC_OWNERSHIP",
            "ACC_OWNERSHIP",
            "ACC_OWNERSHIP",
        ],
        "value_numeric": [
            14.0,
            22.0,
            35.0,
            46.0,
            49.0,
        ],
        "observation_date": pd.to_datetime([
            "2011-12-31",
            "2014-12-31",
            "2017-12-31",
            "2021-12-31",
            "2024-12-31",
        ]),
        "unit": [
            "%",
            "%",
            "%",
            "%",
            "%",
        ],
        "source_name": [
            "Global Findex 2011",
            "Global Findex 2014",
            "Global Findex 2017",
            "Global Findex 2021",
            "Global Findex 2024",
        ],
        "confidence": [
            "high",
            "high",
            "high",
            "high",
            "high",
        ],
    })

    observations = pd.concat(
        [
            observations,
            validated_access_trend,
        ],
        ignore_index=True,
        sort=False,
    )

    observations = observations.drop_duplicates(
        subset=[
            "indicator_code",
            "observation_date",
            "value_numeric",
        ]
    ).copy()

    observations["year"] = (
        observations[
            "observation_date"
        ].dt.year
    )

    observations = observations.sort_values(
        [
            "indicator_code",
            "observation_date",
        ]
    ).reset_index(drop=True)

    indicator_name_map = (
        observations.groupby(
            "indicator_code"
        )["indicator"]
        .first()
        .fillna("")
        .to_dict()
    )

    available_codes = sorted(
        observations[
            "indicator_code"
        ]
        .dropna()
        .unique()
    )

    coverage = (
        observations.groupby(
            "indicator_code"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    default_codes = []

    if "ACC_OWNERSHIP" in available_codes:
        default_codes.append(
            "ACC_OWNERSHIP"
        )

    for code in coverage.index:
        if (
            code not in default_codes
            and len(default_codes) < 4
        ):
            default_codes.append(
                code
            )

    selected_codes = st.multiselect(
        "Select indicators",
        options=available_codes,
        default=default_codes,
        format_func=lambda code: (
            f"{code} — "
            f"{indicator_name_map.get(code, '')}"
        ).rstrip(" —"),
    )

    minimum_year = int(
        observations["year"].min()
    )

    maximum_year = int(
        observations["year"].max()
    )

    if minimum_year < maximum_year:
        year_range = st.slider(
            "Date range",
            min_value=minimum_year,
            max_value=maximum_year,
            value=(
                minimum_year,
                maximum_year,
            ),
        )

    else:
        year_range = (
            minimum_year,
            maximum_year,
        )

        st.caption(
            f"Only observations from "
            f"{minimum_year} are available."
        )

    normalize = st.checkbox(
        "Normalize indicators to 100 at "
        "their first observation",
        value=True,
    )

    filtered_trends = observations[
        observations[
            "indicator_code"
        ].isin(selected_codes)
        & observations["year"].between(
            year_range[0],
            year_range[1],
        )
    ].copy()

    filtered_trends = filtered_trends.sort_values(
        [
            "indicator_code",
            "observation_date",
        ]
    ).reset_index(drop=True)

    if filtered_trends.empty:
        st.warning(
            "Select at least one indicator with "
            "data in the selected date range."
        )

    else:
        filtered_trends["series_label"] = (
            filtered_trends[
                "indicator_code"
            ].map(
                lambda code: (
                    f"{code} — "
                    f"{indicator_name_map.get(code, '')}"
                ).rstrip(" —")
            )
        )

        y_column = "value_numeric"
        y_label = "Observed value"

        if normalize:

            def normalize_series(
                series: pd.Series,
            ) -> pd.Series:
                first_value = (
                    series.iloc[0]
                )

                if first_value == 0:
                    return series

                return (
                    series
                    / first_value
                    * 100
                )

            filtered_trends[
                "normalized_value"
            ] = filtered_trends.groupby(
                "indicator_code"
            )["value_numeric"].transform(
                normalize_series
            )

            y_column = (
                "normalized_value"
            )

            y_label = (
                "Index "
                "(first observation = 100)"
            )

        trend_hover_data = {
            "indicator_code": True,
            "value_numeric": ":,.2f",
            "observation_date": "|%Y-%m-%d",
        }

        for optional_column in [
            "indicator",
            "unit",
            "source_name",
        ]:
            if optional_column in filtered_trends.columns:
                trend_hover_data[
                    optional_column
                ] = True

        trend_figure = px.line(
            filtered_trends,
            x="observation_date",
            y=y_column,
            color="series_label",
            markers=True,
            hover_data=trend_hover_data,
            labels={
                "observation_date": (
                    "Observation date"
                ),
                y_column: y_label,
                "series_label": (
                    "Indicator"
                ),
            },
        )

        trend_figure.update_traces(
            line_width=3,
            marker_size=8,
        )

        trend_figure.update_layout(
            height=520,
            hovermode="x unified",
            legend_title_text=(
                "Indicator"
            ),
        )

        trend_figure.update_xaxes(
            tickformat="%Y",
        )

        st.plotly_chart(
            trend_figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )

        download_csv_button(
            filtered_trends,
            "Download filtered trends",
            "filtered_indicator_trends.csv",
        )

    st.subheader(
        "Channel comparison"
    )

    channel_codes = [
        "USG_P2P_COUNT",
        "USG_ATM_COUNT",
        "USG_TELEBIRR_USERS",
        "USG_MPESA_USERS",
    ]

    channel_rows = []

    for code in channel_codes:
        row = latest_indicator_row(
            code
        )

        if row is None:
            continue

        value = float(
            row["value_numeric"]
        )

        unit = row.get(
            "unit",
            "",
        )

        channel_rows.append({
            "indicator": row.get(
                "indicator",
                code,
            ),
            "indicator_code": code,
            "value": value,
            "unit": unit,
            "display_value": (
                format_value_with_unit(
                    value,
                    unit,
                )
            ),
        })

    channel_df = pd.DataFrame(
        channel_rows
    )

    if channel_df.empty:
        st.info(
            "No channel indicators are "
            "available for comparison."
        )

    else:
        channel_figure = px.bar(
            channel_df.sort_values(
                "value"
            ),
            x="value",
            y="indicator",
            orientation="h",
            color="indicator_code",
            text="display_value",
            log_x=True,
            hover_data={
                "indicator_code": True,
                "unit": True,
                "value": ":,.2f",
            },
            labels={
                "value": (
                    "Latest value "
                    "(logarithmic scale)"
                ),
                "indicator": "",
            },
        )

        channel_figure.update_traces(
            textposition="outside"
        )

        channel_figure.update_layout(
            height=430,
            showlegend=False,
        )

        st.plotly_chart(
            channel_figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )


# =========================================================
# CORRECTED EVENT IMPACTS PAGE
# =========================================================

elif page == "Event Impacts":

    st.header(
        "Event-Indicator Impacts"
    )

    st.write(
        "Positive scores represent supportive "
        "modeled relationships. Negative scores "
        "represent constraining relationships."
    )

    # Consistent color scale:
    # Blue = negative
    # White = neutral
    # Red = positive
    impact_color_scale = [
        [0.00, "#2166AC"],
        [0.25, "#67A9CF"],
        [0.50, "#F7F7F7"],
        [0.75, "#EF8A62"],
        [1.00, "#B2182B"],
    ]

    impact_view = impact_df.copy()

    impact_view["effect_score"] = pd.to_numeric(
        impact_view["effect_score"],
        errors="coerce",
    )

    impact_view = impact_view.dropna(
        subset=["effect_score"]
    ).copy()

    impact_view["absolute_effect"] = (
        impact_view[
            "effect_score"
        ].abs()
    )

    impact_view["relationship"] = (
        impact_view[
            "event_name_resolved"
        ]
        .fillna("Unknown event")
        .astype(str)
        + " → "
        + impact_view[
            "related_indicator"
        ]
        .fillna("Unknown indicator")
        .astype(str)
    )

    matrix_values = association_matrix.to_numpy(
        dtype=float
    )

    matrix_maximum = (
        float(
            np.nanmax(
                np.abs(matrix_values)
            )
        )
        if matrix_values.size > 0
        else 0.0
    )

    relationship_maximum = (
        float(
            impact_view[
                "absolute_effect"
            ].max()
        )
        if not impact_view.empty
        else 0.0
    )

    effect_limit = max(
        1.0,
        matrix_maximum,
        relationship_maximum,
    )

    effect_limit = float(
        np.ceil(effect_limit)
    )

    st.subheader(
        "Event-Indicator Association Matrix"
    )

    heatmap = go.Figure(
        data=go.Heatmap(
            z=association_matrix.values,
            x=association_matrix.columns.tolist(),
            y=association_matrix.index.tolist(),
            colorscale=impact_color_scale,
            zmin=-effect_limit,
            zmax=effect_limit,
            zmid=0,
            colorbar={
                "title": {
                    "text": "Effect score"
                },
                "tickmode": "linear",
                "tick0": -effect_limit,
                "dtick": 1,
            },
            hovertemplate=(
                "<b>Event:</b> %{y}<br>"
                "<b>Indicator:</b> %{x}<br>"
                "<b>Effect score:</b> %{z:.2f}"
                "<extra></extra>"
            ),
        )
    )

    heatmap.update_layout(
        height=max(
            540,
            48 * len(
                association_matrix.index
            ),
        ),
        xaxis_title=(
            "Financial-Inclusion Indicator"
        ),
        yaxis_title="Event",
        margin={
            "l": 20,
            "r": 20,
            "t": 30,
            "b": 150,
        },
    )

    heatmap.update_xaxes(
        tickangle=-45,
        automargin=True,
    )

    heatmap.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        heatmap,
        use_container_width=True,
        config={
            "displaylogo": False,
            "responsive": True,
        },
    )

    st.caption(
        "Blue cells represent negative or "
        "constraining relationships. Red cells "
        "represent positive or supportive "
        "relationships. White indicates neutral "
        "or unavailable relationships."
    )

    st.subheader(
        "Strongest Modeled Relationships"
    )

    if "pillar" in impact_view.columns:
        available_pillars = sorted(
            impact_view["pillar"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

    else:
        available_pillars = []

    if available_pillars:
        selected_pillars = st.multiselect(
            "Pillars",
            options=available_pillars,
            default=available_pillars,
        )

        filtered_impacts = impact_view[
            impact_view["pillar"]
            .fillna("")
            .astype(str)
            .isin(selected_pillars)
        ].copy()

    else:
        filtered_impacts = (
            impact_view.copy()
        )

        st.caption(
            "No pillar field was available, "
            "so all relationships are shown."
        )

    maximum_relationships = max(
        5,
        min(
            15,
            len(filtered_impacts)
            if not filtered_impacts.empty
            else 5,
        ),
    )

    default_relationships = min(
        10,
        maximum_relationships,
    )

    number_to_show = st.slider(
        "Relationships to display",
        min_value=5,
        max_value=maximum_relationships,
        value=default_relationships,
        step=1,
    )

    selected_impacts = (
        filtered_impacts
        .nlargest(
            number_to_show,
            "absolute_effect",
        )
        .sort_values(
            "effect_score",
            ascending=True,
        )
        .copy()
    )

    if selected_impacts.empty:
        st.info(
            "No modeled relationships match "
            "the selected filters."
        )

    else:
        impact_hover_data = {
            "effect_score": ":.2f",
        }

        for column in [
            "impact_direction",
            "impact_magnitude",
            "lag_months",
            "confidence",
            "pillar",
        ]:
            if column in selected_impacts.columns:
                impact_hover_data[
                    column
                ] = True

        impact_figure = px.bar(
            selected_impacts,
            x="effect_score",
            y="relationship",
            orientation="h",
            color="effect_score",
            color_continuous_scale=(
                impact_color_scale
            ),
            color_continuous_midpoint=0,
            range_color=(
                -effect_limit,
                effect_limit,
            ),
            hover_data=impact_hover_data,
            labels={
                "effect_score": (
                    "Standardized relative effect"
                ),
                "relationship": "",
            },
        )

        impact_figure.add_vline(
            x=0,
            line_dash="dash",
            line_width=1,
            line_color="gray",
        )

        impact_figure.update_layout(
            height=max(
                460,
                46 * len(
                    selected_impacts
                ),
            ),
            coloraxis_colorbar={
                "title": (
                    "Standardized "
                    "relative effect"
                ),
                "tickmode": "linear",
                "tick0": -effect_limit,
                "dtick": 1,
            },
            margin={
                "l": 20,
                "r": 20,
                "t": 30,
                "b": 30,
            },
        )

        impact_figure.update_xaxes(
            range=[
                -effect_limit,
                effect_limit,
            ],
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="gray",
        )

        impact_figure.update_yaxes(
            automargin=True,
        )

        st.plotly_chart(
            impact_figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )

        st.caption(
            "Relationships are ranked by "
            "absolute effect strength. A larger "
            "bar represents a stronger modeled "
            "association."
        )

        table_columns = [
            column
            for column in [
                "event_name_resolved",
                "pillar",
                "related_indicator",
                "impact_direction",
                "impact_magnitude",
                "effect_score",
                "lag_months",
                "confidence",
            ]
            if column in selected_impacts.columns
        ]

        relationship_table = (
            selected_impacts[
                table_columns
            ]
            .sort_values(
                "effect_score",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        if (
            "effect_score"
            in relationship_table.columns
        ):
            relationship_table[
                "effect_score"
            ] = relationship_table[
                "effect_score"
            ].round(2)

        st.dataframe(
            relationship_table,
            use_container_width=True,
            hide_index=True,
        )

    download_csv_button(
        impact_view,
        "Download impact model data",
        "event_impact_link_summary.csv",
    )


# =========================================================
# FORECASTS PAGE
# =========================================================

elif page == "Forecasts":

    st.header(
        "Access and Usage Forecasts"
    )

    st.write(
        "Compare conservative, baseline, "
        "and optimistic forecasts for "
        "2025–2027."
    )

    dimension = st.selectbox(
        "Forecast dimension",
        [
            "Access",
            "Usage",
        ],
    )

    comparison_mode = st.radio(
        "Model selection",
        [
            "Compare all scenarios",
            "Focus on one scenario",
        ],
        horizontal=True,
    )

    scenarios = [
        "Conservative",
        "Baseline",
        "Optimistic",
    ]

    if comparison_mode == (
        "Focus on one scenario"
    ):
        selected_scenarios = [
            st.selectbox(
                "Scenario",
                scenarios,
                index=1,
            )
        ]

    else:
        selected_scenarios = scenarios

    forecast_subset = forecast_df[
        forecast_df["dimension"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq(dimension.lower())
        & forecast_df["scenario"]
        .fillna("")
        .astype(str)
        .isin(selected_scenarios)
    ].copy()

    scenario_colors = {
        "Conservative": "#f59e0b",
        "Baseline": "#16a34a",
        "Optimistic": "#dc2626",
    }

    interval_colors = {
        "Conservative": (
            "rgba(245,158,11,0.16)"
        ),
        "Baseline": (
            "rgba(22,163,74,0.16)"
        ),
        "Optimistic": (
            "rgba(220,38,38,0.16)"
        ),
    }

    forecast_figure = go.Figure()

    if dimension == "Access":
        forecast_figure.add_trace(
            go.Scatter(
                x=access_history["year"],
                y=access_history[
                    "access_percent"
                ],
                mode="lines+markers",
                name="Historical Access",
                line={
                    "color": "#3b82f6",
                    "width": 3,
                },
                marker={
                    "size": 8
                },
            )
        )

        y_title = (
            "Adults with an account (%)"
        )

    else:
        forecast_figure.add_trace(
            go.Scatter(
                x=[2024],
                y=[usage_baseline],
                mode="markers",
                marker={
                    "size": 12,
                    "color": "#3b82f6",
                },
                name=(
                    "2024 Usage baseline"
                ),
            )
        )

        y_title = (
            "Mobile money "
            "activity rate (%)"
        )

    for scenario in selected_scenarios:
        scenario_data = forecast_subset[
            forecast_subset["scenario"]
            .astype(str)
            .eq(scenario)
        ].sort_values("year")

        if scenario_data.empty:
            continue

        forecast_figure.add_trace(
            go.Scatter(
                x=scenario_data["year"],
                y=scenario_data[
                    "upper_90_percent"
                ],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        forecast_figure.add_trace(
            go.Scatter(
                x=scenario_data["year"],
                y=scenario_data[
                    "lower_90_percent"
                ],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=(
                    interval_colors[
                        scenario
                    ]
                ),
                name=(
                    f"{scenario} "
                    "90% interval"
                ),
                hoverinfo="skip",
            )
        )

        forecast_figure.add_trace(
            go.Scatter(
                x=scenario_data["year"],
                y=scenario_data[
                    "forecast_percent"
                ],
                mode="lines+markers",
                name=(
                    f"{scenario} forecast"
                ),
                line={
                    "color": (
                        scenario_colors[
                            scenario
                        ]
                    ),
                    "width": 3,
                },
                marker={
                    "size": 8
                },
                hovertemplate=(
                    f"<b>{scenario}</b><br>"
                    "Year: %{x}<br>"
                    "Forecast: %{y:.1f}%"
                    "<extra></extra>"
                ),
            )
        )

    forecast_figure.add_vline(
        x=2024,
        line_dash="dash",
        annotation_text=(
            "Forecast begins"
        ),
        annotation_position="top left",
    )

    if dimension == "Access":
        forecast_figure.add_hline(
            y=60,
            line_dash="dot",
            annotation_text=(
                "60% target"
            ),
            annotation_position="top right",
        )

    forecast_figure.update_layout(
        title=(
            f"{dimension} Forecast "
            "Scenarios, 2025–2027"
        ),
        height=540,
        xaxis_title="Year",
        yaxis_title=y_title,
        yaxis_range=[
            0,
            100,
        ],
        hovermode="x unified",
    )

    st.plotly_chart(
        forecast_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "responsive": True,
        },
    )

    st.subheader(
        "Key projected milestones"
    )

    milestone_table = (
        forecast_subset[
            forecast_subset[
                "year"
            ].eq(2027)
        ][
            [
                "scenario",
                "forecast_percent",
                "lower_90_percent",
                "upper_90_percent",
            ]
        ]
        .copy()
        .round(1)
    )

    milestone_table.columns = [
        "Scenario",
        "2027 forecast (%)",
        "90% lower (%)",
        "90% upper (%)",
    ]

    st.dataframe(
        milestone_table,
        use_container_width=True,
        hide_index=True,
    )

    download_csv_button(
        forecast_df,
        "Download forecast results",
        "forecasts_2025_2027.csv",
    )


# =========================================================
# INCLUSION PROJECTIONS PAGE
# =========================================================

elif page == "Inclusion Projections":

    st.header(
        "Progress Toward the 60% Target"
    )

    st.write(
        "Explore how each Access scenario "
        "progresses toward the 60% target."
    )

    selected_scenario = st.selectbox(
        "Scenario",
        [
            "Conservative",
            "Baseline",
            "Optimistic",
        ],
        index=1,
    )

    access_projection = forecast_df[
        forecast_df["dimension"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("access")
        & forecast_df["scenario"]
        .fillna("")
        .astype(str)
        .eq(selected_scenario)
    ].sort_values("year")

    projection_data = pd.concat(
        [
            pd.DataFrame({
                "year": [2024],
                "forecast_percent": [
                    49.0
                ],
            }),
            access_projection[
                [
                    "year",
                    "forecast_percent",
                ]
            ],
        ],
        ignore_index=True,
    )

    (
        left_column,
        right_column,
    ) = st.columns(
        [
            1.4,
            1,
        ]
    )

    with left_column:
        projection_figure = px.line(
            projection_data,
            x="year",
            y="forecast_percent",
            markers=True,
            labels={
                "year": "Year",
                "forecast_percent": (
                    "Adults with an "
                    "account (%)"
                ),
            },
        )

        projection_figure.add_hline(
            y=60,
            line_dash="dash",
            annotation_text=(
                "60% target"
            ),
            annotation_position="top right",
        )

        projection_figure.update_traces(
            line_width=3,
            marker_size=9,
        )

        projection_figure.update_layout(
            height=430,
            yaxis_range=[
                0,
                100,
            ],
        )

        st.plotly_chart(
            projection_figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )

    if access_projection.empty:
        projection_2027 = np.nan

    else:
        projection_2027 = float(
            access_projection.iloc[-1][
                "forecast_percent"
            ]
        )

    with right_column:
        if pd.isna(projection_2027):
            st.warning(
                "No 2027 projection was found."
            )

        else:
            gauge = go.Figure(
                go.Indicator(
                    mode=(
                        "gauge+number+delta"
                    ),
                    value=projection_2027,
                    number={
                        "suffix": "%",
                        "valueformat": ".1f",
                    },
                    delta={
                        "reference": 60,
                        "relative": False,
                    },
                    title={
                        "text": (
                            "Projected Access "
                            "in 2027"
                        )
                    },
                    gauge={
                        "axis": {
                            "range": [
                                0,
                                100,
                            ]
                        },
                        "bar": {
                            "color": "#3b82f6"
                        },
                        "steps": [
                            {
                                "range": [
                                    0,
                                    49,
                                ],
                                "color": (
                                    "#334155"
                                ),
                            },
                            {
                                "range": [
                                    49,
                                    60,
                                ],
                                "color": (
                                    "#1e40af"
                                ),
                            },
                            {
                                "range": [
                                    60,
                                    100,
                                ],
                                "color": (
                                    "#166534"
                                ),
                            },
                        ],
                        "threshold": {
                            "line": {
                                "color": (
                                    "#ef4444"
                                ),
                                "width": 4,
                            },
                            "value": 60,
                        },
                    },
                )
            )

            gauge.update_layout(
                height=360
            )

            st.plotly_chart(
                gauge,
                use_container_width=True,
                config={
                    "displaylogo": False,
                    "responsive": True,
                },
            )

            gap = (
                60
                - projection_2027
            )

            if gap > 0:
                st.info(
                    f"The "
                    f"{selected_scenario.lower()} "
                    f"scenario remains "
                    f"{gap:.1f} percentage "
                    "points below the 60% "
                    "target in 2027."
                )

            else:
                st.success(
                    "The selected scenario "
                    "reaches or exceeds the "
                    "60% target by 2027."
                )

    st.subheader(
        "Consortium questions"
    )

    with st.expander(
        "What appears to drive "
        "financial inclusion?",
        expanded=True,
    ):
        st.write(
            "The analysis identifies product "
            "availability, digital identity, "
            "interoperability, agent and merchant "
            "networks, affordability, and active "
            "customer usage as important drivers."
        )

    with st.expander(
        "Why did ownership grow only three "
        "percentage points from 2021 to 2024?"
    ):
        st.write(
            "Registered accounts are not the same "
            "as unique active adult users. Inactive "
            "accounts, duplicate registrations, "
            "existing bank customers, affordability "
            "constraints, and limited use cases may "
            "reduce conversion into measured Access."
        )

    with st.expander(
        "Which events have the largest "
        "potential impact?"
    ):
        st.write(
            "Major mobile-money launches, P2P "
            "expansion, digital identity, "
            "interoperability, affordability "
            "changes, and infrastructure investment "
            "have the strongest modeled associations."
        )

    with st.expander(
        "What are the main uncertainties?"
    ):
        st.write(
            "Access contains only five national "
            "survey observations, while Usage has "
            "only one comparable percentage baseline. "
            "Multiple events overlap, and "
            "administrative counts differ from "
            "survey-based inclusion measures."
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Scenario forecasts should be interpreted "
    "with the documented assumptions and limitations."
)