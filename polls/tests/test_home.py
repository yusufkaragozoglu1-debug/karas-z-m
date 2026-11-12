from django.test import TestCase


class HomeTests(TestCase):
    def test_home_renders(self):
        response = self.client.get("/")
        self.assertContains(response, "Kararsız mı kaldın? Topluluğa sor!")
        self.assertContains(response, '<html lang="tr">')

    def test_404_template(self):
        response = self.client.get("/yok-boyle-bir-sayfa/")
        self.assertEqual(response.status_code, 404)
