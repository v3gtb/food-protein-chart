from dataclasses import dataclass
from functools import lru_cache
import numpy as np
import json
from tabulate import tabulate
from typing import Optional
from pprint import pprint


@dataclass
@dataclass(frozen=True)
class RawRelevantNutrients:
    energy_kcal: Optional[float]
    protein_g: Optional[float]
    carb_by_diff_g: Optional[float]
    total_lipid_g: Optional[float]
    fiber_g: Optional[float]
    alcohol_g: Optional[float]

    @property
    def carb_kcal(self):
        return self.carb_by_diff_g * 4

    @property
    def protein_kcal(self):
        return self.protein_g * 4

    @property
    def fat_kcal(self):
        return self.total_lipid_g * 9

    @property
    def fiber_kcal(self):
        return self.fiber_g * 0

    @property
    def alcohol_kcal(self):
        return self.alcohol_g * 7

    @property
    def energy_from_constituents_kcal(self):
        return (
            self.carb_kcal
            + self.protein_kcal
            + self.fat_kcal
            + self.fiber_kcal
            + self.alcohol_kcal
        )

    @classmethod
    def from_fooddata_dict(cls, d) -> "RawRelevantNutrients":
        l = d["foodNutrients"]
        nutrients_d = cls._extract_nutrients_and_units_by_names(
            l,
            [
                "Energy",
                "Total lipid (fat)",
                "Protein",
                "Carbohydrate, by difference",
                "Fiber, total dietary",
                "Alcohol, ethyl",
            ],
        )
        return cls(
            energy_kcal=nutrients_d.get(("Energy", "kcal")),
            protein_g=nutrients_d.get(("Protein", "g")),
            carb_by_diff_g=nutrients_d.get(
                ("Carbohydrate, by difference", "g")
            ),
            total_lipid_g=nutrients_d.get(("Total lipid (fat)", "g")),
            fiber_g=nutrients_d.get(("Fiber, total dietary", "g")),
            alcohol_g=nutrients_d.get(("Alcohol, ethyl", "g")),
        )

    @classmethod
    def _extract_nutrients_and_units_by_names(cls, l, names=None) -> dict:
        if not names:
            return {}
        return {
            (
                nutrient["nutrient"]["name"],
                nutrient["nutrient"]["unitName"],
            ): nutrient["amount"]
            for nutrient in l
            if nutrient["nutrient"]["name"] in names
        }


@dataclass(frozen=True)
class RawFood:
    fdc_id: int
    description: str
    nutrients: RawRelevantNutrients

    @classmethod
    def from_fooddata_dict(cls, d):
        return cls(
            description=d["description"],
            fdc_id=d["fdcId"],
            nutrients=RawRelevantNutrients.from_fooddata_dict(d),
        )

    @property
    @lru_cache
    def energy_discrepancy_kcal(self):
        return abs(
            self.nutrients.energy_from_constituents_kcal
            - self.nutrients.energy_kcal
        )

    @property
    @lru_cache
    def protein_energy_fraction_based_on_constituents(self):
        if not self.nutrients.energy_from_constituents_kcal:
            return None
        return (
            self.nutrients.protein_kcal
            / self.nutrients.energy_from_constituents_kcal
        )

    @property
    @lru_cache
    def protein_energy_fraction_based_on_given_energy(self):
        if not self.nutrients.energy_kcal:
            return None
        return self.nutrients.protein_kcal / self.nutrients.energy_kcal

    @property
    @lru_cache
    def protein_energy_fraction(self):
        if (
            self.protein_energy_fraction_based_on_given_energy is None
            or self.protein_energy_fraction_based_on_constituents is None
        ):
            return None
        return np.mean(
            [
                self.protein_energy_fraction_based_on_given_energy,
                self.protein_energy_fraction_based_on_constituents,
            ]
        )


def main():
    with open("FoodData_Central_survey_food_json_2021-10-28.json") as f:
        l = json.load(f)["SurveyFoods"]
    with open(
        "VegAttributes_for_FoodData_Central_survey_and_sr_legacy_food_json_2021-10-28.json"
    ) as f:
        va = {x["fdcId"]: x["vegCategory"] for x in json.load(f)}

    # debug
    for d in l:
        if "oat bran, uncooked" in d["description"].lower():
            pprint(d["foodNutrients"])
    # /

    print("All nutrients in dataset:")
    all_nutrients_and_units = set(
        (n["nutrient"]["name"], n["nutrient"]["unitName"])
        for x in l
        for n in x["foodNutrients"]
    )
    print(tabulate(sorted(all_nutrients_and_units)))

    raw_foods = [RawFood.from_fooddata_dict(x) for x in l]

    print("Discrepancies between given energy and calculated sum:")
    foods_sorted_by_energy_discrepancy = sorted(
        raw_foods, key=lambda food: food.energy_discrepancy_kcal
    )
    print(
        tabulate(
            [
                (food.description[:50], food.energy_discrepancy_kcal)
                for food in foods_sorted_by_energy_discrepancy
            ]
        )
    )

    print("Protein energy fractions:")
    foods_sorted_by_protein_energy_fraction = sorted(
        [
            food
            for food in raw_foods
            if food.protein_energy_fraction is not None
        ],
        key=lambda x: x.protein_energy_fraction,
    )
    print(
        tabulate(
            [
                (
                    food.description[:50],
                    f"{food.protein_energy_fraction_based_on_given_energy*100:.1f}%",
                    f"{food.protein_energy_fraction_based_on_constituents*100:.1f}%",
                    "->",
                    f"{food.protein_energy_fraction*100:.1f}%",
                )
                for food in foods_sorted_by_protein_energy_fraction
            ]
        )
    )

    # df-ify and save
    import pandas as pd
    df = pd.DataFrame.from_records(
        {
            "fdc_id": food.fdc_id,
            "description": food.description,
            "protein_g": food.nutrients.protein_g,
            "protein_energy_percent": food.protein_energy_fraction*100,
            "veg_category": (
                va
                .get(food.fdc_id, "UNCATEGORIZED")
                .lower()
                .replace("_", " ")
                .replace("vegan vegetarian", "vegan, vegetarian")
                .capitalize()
            ),
            "url": (
                f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{food.fdc_id}"
            ),

        }
        for food in foods_sorted_by_protein_energy_fraction
    )
    df.to_csv("plot_data.csv")


if __name__ == "__main__":
    main()
