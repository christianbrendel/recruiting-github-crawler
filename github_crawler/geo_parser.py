import os
import typing as t

import pandas as pd


class GeoParser:
    def __init__(self):
        p = os.path.dirname(os.path.abspath(__file__))
        p = os.path.join(p, "assets", "worldcities.csv")
        df = pd.read_csv(p)
        df = df[["city", "city_ascii", "country"]]
        for k in ["city", "city_ascii", "country"]:
            df[k] = df[k].str.lower()
        self.df = df.drop_duplicates(subset=["city", "country"])

    def parse_location(self, location: str) -> t.Tuple[t.List, t.List]:
        """Parse some string to find the geo location.

        Args:
            location (str): Some string, e.g "Berlin, Europe"

        Returns:
            t.Tuple[t.List, t.List]: List of estimaed countries and list of estimated
                cities.
        """
        if type(location) is not str:
            return [], []

        locs = [loc.strip().lower() for loc in location.split(",")]

        # check if a city matches exactly
        m_city_matches = self.df.city == "?@#"  # mask of falses
        for loc in locs:
            m_city_matches |= self.df.city == loc
            m_city_matches |= self.df.city == loc
        estimated_cities = self.df[m_city_matches].city_ascii.unique().tolist()

        # check if a country matches
        m_country_matches = self.df.country == "?@#"  # mask of falses
        for loc in locs:
            m_country_matches |= self.df.country == loc
        estimated_countries = self.df[m_country_matches].country.unique().tolist()

        # in case the estimated country is still none l
        if len(estimated_countries) == 0 and len(estimated_cities) > 0:
            estimated_countries = (
                self.df[self.df.city.isin(estimated_cities)].country.unique().tolist()
            )

        return estimated_countries, estimated_cities

    def get_eu_countries(self):
        return [
            "austria",
            "belgium",
            "bulgaria",
            "croatia",
            "republic of cyprus",
            "czech republic",
            "denmark",
            "estonia",
            "finland",
            "france",
            "germany",
            "greece",
            "hungary",
            "ireland",
            "italy",
            "latvia",
            "lithuania",
            "luxembourg",
            "malta",
            "netherlands",
            "poland",
            "portugal",
            "romania",
            "slovakia",
            "slovenia",
            "spain",
            "Sweden",
        ]
