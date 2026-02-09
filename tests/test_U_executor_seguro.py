from classes.executor_de_operacoes import ExecutorSeguro, LogMixin, SafeRenameMixin, ExecutorDeOperacoes


def test_u_mro_executor_seguro():
    mro = ExecutorSeguro.mro()
    assert mro[0] is ExecutorSeguro
    assert mro[1] is LogMixin
    assert mro[2] is SafeRenameMixin
    assert mro[3] is ExecutorDeOperacoes
