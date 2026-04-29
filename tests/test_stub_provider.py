from llm.stub_provider import StubProvider


async def test_stub_casting_one_vacancy():
    text = "Кастинг на сериал. Девушка 25-30 лет, нужна на главную роль."
    out = await StubProvider().extract(text)
    assert out.is_casting is True
    assert len(out.vacancies) == 1
    v = out.vacancies[0]
    assert v.gender == "female"
    assert v.age_min == 25
    assert v.age_max == 30


async def test_stub_non_casting_empty_vacancies():
    out = await StubProvider().extract("Продаю гараж недорого")
    assert out.is_casting is False
    assert out.vacancies == []
