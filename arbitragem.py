import logging
import uuid
from datetime import datetime
from uteis.corretora import Corretora
from uteis.util import Util
from uteis.googleSheets import GoogleSheets

class Arbitragem:

    def simples(corretoraCompra:Corretora, corretoraVenda:Corretora, ativo, executarOrdens = False):
        
        
        try:
            fiz_arb = False
            pnl = 0
            pnl_real = 0
            ordem_compra = corretoraCompra.ordem
            ordem_venda = corretoraVenda.ordem

            corretoraCompra.atualizar_saldo()
            corretoraVenda.atualizar_saldo()

            #carrego os books de ordem mais recentes, a partir daqui precisamos ser rapidos!!! é a hora do show!!
            corretoraVenda.obter_ordem_book_por_indice(ativo,'brl',0,True,True)
            corretoraCompra.obter_ordem_book_por_indice(ativo,'brl',0,True,True)
        
            preco_de_compra = corretoraCompra.livro.preco_compra #primeiro no book de ordens
            preco_de_venda = corretoraVenda.livro.preco_venda #primeiro no book de ordens

            #se tiver arbitragem, a magica começa!
            if preco_de_compra < preco_de_venda: 

                quantidade_de_compra = corretoraCompra.livro.quantidade_compra #qtd no book de ordens
                quantidade_de_venda = corretoraVenda.livro.quantidade_venda #qtd no book de ordens

                colchao_de_liquidez = 0.98

                quanto_posso_comprar = colchao_de_liquidez*corretoraCompra.saldo['brl']/corretoraCompra.livro.preco_venda #saldo em reais * colchão
                quanto_posso_vender = colchao_de_liquidez*corretoraVenda.saldo[ativo] #saldo em cripto * colchão

                # Obtendo a menor quantidade de compra e venda entre as corretoras que tenho saldo para negociar
                qtdNegociada = min(quantidade_de_compra, quantidade_de_venda,quanto_posso_comprar,quanto_posso_vender)
             
                # Verifica em termos financeiros levando em conta as corretagens de compra e venda, se a operação vale a pena
                vou_pagar = qtdNegociada*preco_de_compra*(1+corretoraCompra.corretagem_mercado)
                vou_ganhar = qtdNegociada*preco_de_venda*(1-corretoraVenda.corretagem_mercado)

                pnl = vou_ganhar - vou_pagar
                
                #define pnl minimo para aceitarmos o trade
                fracao_do_caixa = corretoraCompra.saldo['brl']/(corretoraCompra.saldo['brl']+corretoraVenda.saldo['brl'])
                
                pnl_minimo = -1
                pnl_minimo = 0.1 if fracao_do_caixa<0.9 else pnl_minimo

                rentabilidade_minima = -10/10000
                rentabilidade_minima = 0 if fracao_do_caixa<0.95 else rentabilidade_minima
                rentabilidade_minima = 1/10000 if fracao_do_caixa<0.8 else rentabilidade_minima
                rentabilidade_minima = 2/10000 if fracao_do_caixa<0.5 else rentabilidade_minima
                rentabilidade_minima = 10/10000 if fracao_do_caixa<0.2 else rentabilidade_minima # se eu tenho pouca grana na corretoracompra, então só faz o trade se der um bambá bom
                rentabilidade_minima = 200/10000 if fracao_do_caixa<0.1 else rentabilidade_minima # se tenho muito pouco caixa nao é pra usar na arb nem fodendo
                
                if qtdNegociada !=0:
                    # Teste se o financeiro com a corretagem é menor que o pnl da operação
                    if (pnl/vou_pagar)>rentabilidade_minima and pnl>pnl_minimo:#só fazemos se a rentabilidade for maior que isso
                        # Condição para que verificar se o saldo em reais e crypto são suficientes para a operação
                        if (vou_pagar > Util.retorna_menor_valor_compra(ativo)) and (qtdNegociada > Util.retorna_menor_quantidade_venda(ativo)):
                            #se tenho saldo, prossigo
                            if (corretoraCompra.saldo['brl'] >= vou_pagar) and (corretoraVenda.saldo[ativo] >= qtdNegociada): 
                                
                                fiz_arb = True
                                if executarOrdens:
                                    # Atualiza ordem de compra
                                    ordem_compra.quantidade_enviada = qtdNegociada
                                    ordem_compra.preco_enviado = preco_de_compra
                                    ordem_compra.tipo_ordem = 'market'

                                    ordem_venda.quantidade_enviada = qtdNegociada
                                    ordem_venda.preco_enviado = preco_de_venda
                                    ordem_venda.tipo_ordem = 'market'

                                    quero_comprar_a = round(preco_de_compra,4)
                                    quero_vender_a = round(preco_de_venda,4)

                                    logging.info('Arbitragem: vai vender {}{} @{} na {} que tem {} de saldo e comprar depois @{} na {}'.format(round(qtdNegociada,4),ativo,quero_vender_a,corretoraVenda.nome,corretoraVenda.saldo[ativo],quero_comprar_a,corretoraCompra.nome))
                                    ordem_venda = corretoraVenda.enviar_ordem_venda(ordem_venda,ativo)
                                    ordem_compra = corretoraCompra.enviar_ordem_compra(ordem_compra,ativo)

                                    realmente_paguei = qtdNegociada*ordem_compra.preco_executado*(1+corretoraCompra.corretagem_mercado)
                                    realmente_ganhei = qtdNegociada*ordem_venda.preco_executado*(1-corretoraVenda.corretagem_mercado)

                                    if ordem_compra.preco_executado== 0 or ordem_venda.preco_executado ==0:
                                        pnl_real = 0
                                    else:
                                        pnl_real = realmente_ganhei - realmente_paguei

                                    comprei_a = round(ordem_compra.preco_executado,4)
                                    vendi_a = round(ordem_venda.preco_executado,4)

                                    quantidade_executada_compra = ordem_compra.quantidade_executada
                                    quantidade_executada_venda = ordem_venda.quantidade_executada
                                    
                                    trade_time = Util.excel_date(datetime.now())
                                    trade_id = str(uuid.uuid4())
                                    GoogleSheets().escrever_operacao([ativo,corretoraCompra.nome,comprei_a,quantidade_executada_compra,corretoraVenda.nome,vendi_a,quantidade_executada_venda,pnl_real,'ARBITRAGEM',trade_time,realmente_paguei,realmente_ganhei])
                                    
                                    compra_eh_171 = 0 if quantidade_de_compra<quanto_posso_comprar else 1
                                    venda_eh_171 = 0 if quantidade_de_venda<quanto_posso_vender else 1
                                    custo_corretagem_compra = corretoraCompra.corretagem_mercado*qtdNegociada*ordem_compra.preco_executado
                                    custo_corretagem_venda = corretoraVenda.corretagem_mercado*qtdNegociada*ordem_venda.preco_executado
                                    GoogleSheets().escrever_spot([trade_time,trade_id,'ARBITRAGEM',ativo,corretoraCompra.nome,'COMPRA',comprei_a,quantidade_executada_compra,realmente_paguei,pnl_real/2,preco_de_compra,pnl/2,corretoraCompra.corretagem_mercado,custo_corretagem_compra,compra_eh_171,'FALSE'])
                                    GoogleSheets().escrever_spot([trade_time,trade_id,'ARBITRAGEM',ativo,corretoraVenda.nome,'VENDA',vendi_a,quantidade_executada_venda,realmente_ganhei,pnl_real/2,preco_de_venda,pnl/2,corretoraVenda.corretagem_mercado,custo_corretagem_venda,venda_eh_171,'FALSE'])

                                    if ordem_compra.status.lower() != ordem_compra.descricao_status_executado.lower():
                                        logging.error('Arbitragem: NAO zerou a compra na {}, o status\status executado veio {}\{}'.format(corretoraCompra.nome,ordem_compra.status,ordem_compra.descricao_status_executado))
                                    else:
                                        logging.info('Arbitragem: operou arb de {}! com {}brl de pnl estimado com compra de {}{} @{} na {}'.format(ativo,round(pnl/2,2),round(ordem_compra.quantidade_enviada,4),ativo,round(quero_comprar_a,6),corretoraCompra.nome))
                                        logging.warning('Arbitragem: operou arb de {}! com {}brl de pnl real com compra de {}{} @{} na {}'.format(ativo,round(pnl_real/2,2),round(ordem_compra.quantidade_enviada,4),ativo,ordem_compra.preco_executado,corretoraCompra.nome))
                                        
                                    if ordem_venda.status.lower() != ordem_venda.descricao_status_executado.lower():
                                        logging.error('Arbitragem: NAO zerou a venda na {}, o status\status executado veio {}\{}'.format(corretoraVenda.nome,ordem_venda.status,ordem_venda.descricao_status_executado))
                                    else: 
                                        logging.info('Arbitragem: operou arb de {}! com {}brl de pnl estimado com venda de {}{} @{} na {}'.format(ativo,round(pnl/2,2),round(ordem_venda.quantidade_enviada,4),ativo,round(quero_vender_a,6),corretoraVenda.nome))
                                        logging.warning('Arbitragem: operou arb de {}! com {}brl de pnl real com venda de {}{} @{} na {}'.format(ativo,round(pnl_real/2,2),round(ordem_venda.quantidade_enviada,4),ativo,ordem_venda.preco_executado,corretoraVenda.nome))

                                    return fiz_arb , pnl_real

                            else:
                                logging.info('Arbitragem: nao vai enviar ordem de {} porque saldo em reais {} ou saldo em cripto {} nao é suficiente'.format(ativo,round(corretoraCompra.saldo['brl'],2),corretoraVenda.saldo[ativo]))
                                return fiz_arb , pnl_real
                        else: 
                            logging.info('Arbitragem: nao vai enviar ordem de {} porque qtde {} nao é maior que a minima {} ou o valor a pagar {} nao é maior que o minimo {}'.format(ativo,qtdNegociada,Util.retorna_menor_quantidade_venda(ativo),vou_pagar,Util.retorna_menor_valor_compra(ativo)))
                            return fiz_arb , pnl_real
                    else:
                        logging.info('Arbitragem: nao vai enviar ordem de {} porque comprando na {} o pnl estimado (${}) é menor que o minimo (${}) ou nao atinge nossa rentabilidade minima:({}%>{}/{}*100)'.format(ativo,corretoraCompra.nome,round(pnl,2),round(pnl_minimo,2),round(100*rentabilidade_minima,4),round(pnl,2),round(vou_pagar,2)))
                        return fiz_arb , pnl_real   
                else:
                    logging.info('Arbitragem: acabaram as {} na {} ou acabou o saldo em brl na {}'.format(ativo,corretoraVenda.nome,corretoraCompra.nome))
                    return fiz_arb , pnl_real
            else:
                logging.info('Arbitragem: nao vai comprar {} na {} porque preco compra {} na {} é maior que preco venda {} na {}'.format(ativo,corretoraCompra.nome,round(preco_de_compra,2),corretoraCompra.nome,round(preco_de_venda,2),corretoraVenda.nome))
                return fiz_arb , pnl_real

        except Exception as erro:
            msg_erro = Util.retorna_erros_objeto_exception('Arbitragem: Erro na estratégia de arbitragem, método: simples - ', erro)
            raise Exception(msg_erro)


if __name__ == "__main__":

    from datetime import datetime
    from arbitragem import Arbitragem
    

    logging.basicConfig(filename='Arbitragem.log', level=logging.INFO,
                        format='[%(asctime)s][%(levelname)s][%(message)s]')
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)

    #essa parte executa apenas uma vez
    white_list = Util.obter_white_list()
    white_list = [moeda for moeda in white_list if moeda in Util.obter_lista_de_moedas('arbitragem_status')]
    black_list = []

    corretora_mais_liquida = Util.obter_corretora_de_maior_liquidez()
    corretora_menos_liquida = Util.obter_corretora_de_menor_liquidez()
    
    CorretoraMaisLiquida = Corretora(corretora_mais_liquida)
    CorretoraMenosLiquida = Corretora(corretora_menos_liquida)

    while True:

        lista_de_moedas = [moeda for moeda in white_list if (moeda not in black_list)]

        for moeda in lista_de_moedas:
            try:
                # Instancia das corretoras 
                CorretoraMaisLiquida = Corretora(corretora_mais_liquida)
                CorretoraMenosLiquida = Corretora(corretora_menos_liquida)

                # Roda a arbitragem nas 2 corretoras

                teve_arb = True
                while teve_arb:
                    teve_arb, pnl_real = Arbitragem.simples(CorretoraMaisLiquida, CorretoraMenosLiquida, moeda, True)
                    if pnl_real < -10: #menor pnl aceitavel, do contrario fica de castigo
                        black_list.append(moeda)
                        teve_arb = False #para sair imediatamente do loop
                        logging.warning('Arbitragem: a moeda {} vai ser adicionado ao blacklist porque deu pnl {} menor que {}'.format(moeda,round(pnl_real,2),-10))

                teve_arb = True
                while teve_arb:
                    teve_arb, pnl_real = Arbitragem.simples(CorretoraMenosLiquida, CorretoraMaisLiquida, moeda, True)
                    if pnl_real < -10: #menor pnl aceitavel, do contrario fica de castigo
                        black_list.append(moeda)   
                        teve_arb = False #para sair imediatamente do loop
                        logging.warning('Arbitragem: a moeda {} vai ser adicionado ao blacklist porque deu pnl {} menor que {}'.format(moeda,round(pnl_real,2),-10))
                                
            except Exception as erro:        
                logging.error(erro) 
            
        
        
