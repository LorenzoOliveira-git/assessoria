"""Cinco testes das regras reais, sem chamadas a bancos ou modelos externos."""

import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.escritas import contexto, escrita
from app.schemas import PerfilRequest


class FluxoDeNegocioTests(unittest.TestCase):
    def setUp(self):
        self.perfil = {
            "user_id": " usuario_ci ",
            "renda_mensal": 5000,
            "gasto_fixo_mensal": 2000,
            "horizonte_meses": 12,
            "perfil_investidor": "conservador",
            "restricoes": [" Evitar investimentos de alto risco. "],
        }
        # Substitui somente a fronteira com o banco. A regra e o lote sao reais.
        self.conectar = self.enterContext(patch("app.tools.db.psycopg2.connect"))
        self.persistir = Mock(return_value={"status": "ok", "id": 42})

        @escrita
        def add_transaction(amount, source_text):
            return self.persistir(amount=amount, source_text=source_text)

        self.adicionar = add_transaction

    def test_perfil_valido_normaliza_usuario_e_restricoes(self):
        perfil = PerfilRequest(**self.perfil)

        self.assertEqual(perfil.user_id, "usuario_ci")
        self.assertEqual(perfil.restricoes, ["Evitar investimentos de alto risco."])
        self.assertEqual(perfil.renda_mensal - perfil.gasto_fixo_mensal, 3000)

    def test_perfil_invalido_e_rejeitado(self):
        for alteracao in (
            {"gasto_fixo_mensal": 5000},
            {"gasto_fixo_mensal": 6000},
            {"renda_mensal": 0},
            {"horizonte_meses": 0},
            {"restricoes": [" "]},
            {"user_id": " "},
        ):
            with self.subTest(alteracao=alteracao):
                with self.assertRaises(ValidationError):
                    PerfilRequest(**(self.perfil | alteracao))

    def test_transacao_so_persiste_apos_aprovacao_e_uma_unica_vez(self):
        pergunta = "Gastei R$ 50,00 no mercado."
        with contexto("turno-aprovado", pergunta) as turno:
            pendente = self.adicionar(amount=50, source_text="texto do agente")
            repetida = self.adicionar(amount=50, source_text="outro texto")
            self.assertEqual(pendente["status"], "pendente")
            self.assertFalse(pendente["persistido"])
            self.assertEqual(pendente["operacao_id"], repetida["operacao_id"])
            self.persistir.assert_not_called()
            self.conectar.assert_not_called()

            recibo = turno.concluir(True)
            self.assertIn("R$ 50,00", recibo)
            self.assertEqual(turno.concluir(True), recibo)

        self.persistir.assert_called_once_with(amount=50, source_text=pergunta)
        self.conectar.assert_called_once()
        self.conectar.return_value.commit.assert_called_once()
        self.conectar.return_value.rollback.assert_not_called()
        self.conectar.return_value.close.assert_called_once()

    def test_juiz_reprova_transacao_sem_persistir(self):
        with contexto("turno-reprovado", "Gastei R$ 50,00 no mercado.") as turno:
            self.adicionar(amount=50, source_text="texto do agente")
            resposta = turno.concluir(False)

            self.assertEqual(turno.status, "bloqueado")
            self.assertIn("Nenhuma escrita", resposta)
        self.persistir.assert_not_called()
        self.conectar.assert_not_called()

    def test_valor_diferente_do_informado_nao_e_gravado(self):
        with contexto("turno-valor-incorreto", "Gastei R$ 50,00 no mercado.") as turno:
            resultado = self.adicionar(amount=500, source_text="Gastei R$ 500,00.")
            self.assertEqual(resultado["status"], "error")
            self.assertFalse(resultado["persistido"])
            # Nem a aprovacao posterior pode executar uma intencao invalida.
            resposta = turno.concluir(True)
            self.assertEqual(turno.status, "bloqueado")
            self.assertIn("Nenhuma escrita", resposta)
        self.persistir.assert_not_called()
        self.conectar.assert_not_called()
