from app.services import oecd_service


def test_rankings_cover_2020_to_2023_with_top_ten(real_data_dir):
    rankings = oecd_service.oecd_rankings(real_data_dir)
    assert [year.year for year in rankings.years] == [2020, 2021, 2022, 2023]
    for year in rankings.years:
        assert len(year.countries) == 10
        assert year.country_count >= 10
        rates = [country.rate for country in year.countries]
        assert rates == sorted(rates, reverse=True)
        assert year.countries[0].rank == 1


def test_korea_2023_rate_and_rank(real_data_dir):
    """화면 카드 기준: 2023년 한국 65세 이상 사망률 13.1명, 35개국 중 5위."""
    year_2023 = oecd_service.oecd_rankings(real_data_dir).years[-1]
    assert year_2023.country_count == 35
    korea = next(c for c in year_2023.countries if c.iso3 == "KOR")
    assert (korea.rate, korea.rank) == (13.1, 5)
