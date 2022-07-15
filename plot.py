import altair as alt
import pandas as pd

def main():
    df = pd.read_csv("plot_data.csv")

    tableau20 = {
        "b1": "#4c78a8",
        "b2": "#9ecae9",
        "o1": "#f58518",
        "o2": "#ffbf79",
        "g1": "#54a24b",
        "g2": "#88d27a",
        "y1": "#b79a20",
        "y2": "#f2cf5b",
        "t1": "#439894",
        "t2": "#83bcb6",
        "r1": "#e45756",
        "r2": "#ff9d98",
        "k1": "#79706e",
        "k2": "#bab0ac",
        "p1": "#d67195",
        "p2": "#fcbfd2",
        "v1": "#b279a2",
        "v2": "#d6a5c9",
        "e1": "#9e765f",
        "e2": "#d8b5a5",
    }
    colors = {
        "Vegan": tableau20["g1"],
        "Vegetarian": tableau20["o1"],
        "Omni": tableau20["r1"],
        "Vegan or vegetarian": tableau20["y2"],
        "Vegan or omni": tableau20["e1"],
        "Vegan, vegetarian or omni": tableau20["p1"],
        "Uncategorized": tableau20["k1"],
    }
    colors_list = list(colors.items())

    selection = alt.selection_multi(fields=['veg_category'], bind='legend')

    chart = alt.Chart(df).mark_circle(size=40).encode(
        alt.X(
            'protein_energy_percent',
            title="Protein energy in % of total"
        ),
        alt.Y(
            'protein_g',
            title="Protein weight in % of total"
        ),
        color=alt.Color(
            'veg_category',
            scale=alt.Scale(
                domain=[x[0] for x in colors_list],
                range=[x[1] for x in colors_list],
            ),
            title="Category",
        ),
        opacity=alt.condition(selection, alt.value(1), alt.value(0.1)),
        tooltip=['description', 'veg_category', 'fdc_id'],
        href="url",
    ).add_selection(
        selection
    ).properties(
        width=1080, height=550
    )

    chart['usermeta'] = {
        "embedOptions": {
            'loader': {'target': '_blank'}
        }
    }

    chart.interactive().save("plot.html")


if __name__ == "__main__":
    main()
