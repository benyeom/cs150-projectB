from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd
from pandas_datareader import wb

app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# Custom short names for each indicator
indicators = {
    "EG.ELC.ACCS.ZS": "Access to electricity",
    "EG.CFT.ACCS.ZS": "Access to clean fuels",
    "EG.ELC.FOSL.ZS": "Electricity from fossil sources",
    "EG.ELC.RNWX.KH": "Electricity from renewable sources",
    "EG.ELC.NUCL.ZS": "Electricity from nuclear sources",
}

# Full indicator names for internal use
full_indicators = {
    "EG.ELC.ACCS.ZS": "Access to electricity (% of population)",
    "EG.CFT.ACCS.ZS": "Access to clean fuels and technologies for cooking (% of population)",
    "EG.ELC.FOSL.ZS": "Electricity production from oil, gas and coal sources (% of total)",
    "EG.ELC.RNWX.KH": "Electricity production from renewable sources, excluding hydroelectric (kWh)",
    "EG.ELC.NUCL.ZS": "Electricity production from nuclear sources (% of total)",
}

countries = wb.get_countries()
countries["capitalCity"].replace({"": None}, inplace=True)
countries.dropna(subset=["capitalCity"], inplace=True)
countries = countries[["name", "iso3c"]]
countries = countries.rename(columns={"name": "country"})


def update_wb_data():
    df = wb.download(
        indicator=(list(full_indicators)), country=countries["iso3c"], start=2000, end=2022
    )
    df = df.reset_index()
    df.year = df.year.astype(int)
    df = pd.merge(df, countries, on="country")
    df = df.rename(columns=full_indicators)
    return df


app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                [
                    html.H1("Global Energy Production and Accessibility",
                            style={"textAlign": "center", "marginTop": "30px"}),
                    dcc.Graph(id="my-choropleth", figure={}),
                ],
                width=12,
            )
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Select Data Set:", className="fw-bold",
                                  style={"textDecoration": "underline", "fontSize": 20}),
                        dcc.Dropdown(
                            id="dropdown-indicator",
                            options=[{"label": short_name, "value": indicator} for indicator, short_name in
                                     indicators.items()],
                            value=list(indicators.keys())[0],  # default value using the indicator key
                            clearable=False,
                            style={"width": "100%"},
                        ),
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Label("Select Years:", className="fw-bold",
                                  style={"textDecoration": "underline", "fontSize": 20}),
                        dcc.RangeSlider(
                            id="years-range",
                            min=2000,
                            max=2022,
                            step=1,
                            value=[2000, 2001],
                            marks={
                                year: (str(year) if year % 5 == 0 else f"'{str(year)[-2:]}")
                                for year in range(2000, 2023)
                            },
                        ),
                    ],
                    width=6,
                ),
            ],
            className="my-4",
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.H3("Compare Two Indicators", style={"textAlign": "center", "marginTop": "30px"}),
                    dcc.Dropdown(
                        id="dropdown-indicator-compare",
                        options=[{"label": short_name, "value": indicator} for indicator, short_name in
                                 indicators.items()],
                        value=[list(indicators.keys())[0], list(indicators.keys())[1]],  # default values
                        multi=True,
                        clearable=False,
                        style={"width": "100%"},
                    ),
                    dbc.Button(
                        "Compare",
                        id="compare-button",
                        color="primary",
                        style={"width": "100%", "marginTop": "10px"},
                    ),
                    html.Div(id="compare-output", style={"marginTop": "20px"}),
                ],
                width=12,
            )
        ),
        dcc.Store(id="storage", storage_type="session", data={}),
        dcc.Interval(id="timer", interval=1000 * 60, n_intervals=0),
    ]
)


@app.callback(
    Output("years-range", "max"),
    Input("dropdown-indicator", "value"),
)
def update_slider_max(indicator):
    if indicator in ["EG.ELC.ACCS.ZS", "EG.CFT.ACCS.ZS"]:
        return 2022
    return 2015


@app.callback(Output("storage", "data"), Input("timer", "n_intervals"))
def store_data(n_time):
    dataframe = update_wb_data()
    return dataframe.to_dict("records")


@app.callback(
    Output("my-choropleth", "figure"),
    Input("dropdown-indicator", "value"),
    Input("storage", "data"),
    Input("years-range", "value"),
)
def update_graph(indicator, stored_dataframe, years_chosen):
    dff = pd.DataFrame.from_records(stored_dataframe)
    dff = dff[dff.year.between(years_chosen[0], years_chosen[1])]
    dff = dff.groupby(["iso3c", "country"])[full_indicators[indicator]].mean().reset_index()

    fig = px.choropleth(
        data_frame=dff,
        locations="iso3c",
        color=full_indicators[indicator],
        scope="world",
        hover_data={"iso3c": False, "country": True},
        color_continuous_scale=["#ffffff", "#add8e6"],
    )
    fig.update_layout(
        geo={"projection": {"type": "natural earth"}},
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig


@app.callback(
    Output("compare-output", "children"),
    Input("compare-button", "n_clicks"),
    State("dropdown-indicator-compare", "value"),
    State("storage", "data"),
    State("years-range", "value"),
)
def compare_maps(n_clicks, selected_indicators, stored_dataframe, years_chosen):
    if not n_clicks or len(selected_indicators) != 2:
        return ""

    dff = pd.DataFrame.from_records(stored_dataframe)
    dff = dff[dff.year.between(years_chosen[0], years_chosen[1])]

    fig1 = px.choropleth(
        data_frame=dff,
        locations="iso3c",
        color=full_indicators[selected_indicators[0]],
        scope="world",
        hover_data={"iso3c": False, "country": True},
        color_continuous_scale=["#ffffff", "#add8e6"],
    )
    fig1.update_layout(
        geo={"projection": {"type": "natural earth"}},
        margin=dict(l=50, r=50, t=50, b=50),
        title=indicators[selected_indicators[0]],
    )

    fig2 = px.choropleth(
        data_frame=dff,
        locations="iso3c",
        color=full_indicators[selected_indicators[1]],
        scope="world",
        hover_data={"iso3c": False, "country": True},
        color_continuous_scale=["#ffffff", "#add8e6"],
    )
    fig2.update_layout(
        geo={"projection": {"type": "natural earth"}},
        margin=dict(l=50, r=50, t=50, b=50),
        title=indicators[selected_indicators[1]],
    )

    return html.Div([
        dbc.Col(dcc.Graph(figure=fig1), width=12),
        dbc.Col(dcc.Graph(figure=fig2), width=12),
    ])


if __name__ == "__main__":
    app.run_server(debug=True)





