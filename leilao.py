import time
import logging
from datetime import datetime
from uteis.corretora import Corretora
from uteis.util import Util
from uteis.ordem import Ordem
import math
class Leilao:

    def envia_compra_limitada(corretoraLeilao:Corretora, corretoraZeragem:Corretora, ativo, executarOrdens = False):

        retorno_venda_corretora_leilao = Ordem()
        
        try:
            # Lista de moedas que está rodando de forma parametrizada
            qtd_de_moedas = len(Util.obter_lista_de_moedas())

            #carrego os books de ordem mais recentes, a partir daqui precisamos ser rapidos!!! é a hora do show!!
            corretoraLeilao.book.obter_ordem_book_por_indice(ativo,'brl',0,True)
            corretoraZeragem.book.obter_ordem_book_por_indice(ativo,'brl',0,True)

            preco_que_vou_vender = corretoraLeilao.book.preco_compra-0.01 #primeiro no book de ordens - 1 centavo
            preco_de_zeragem = corretoraZeragem.book.preco_compra # zeragem no primeiro book de ordens

            # Valida se existe oportunidade de leilão
            if (preco_que_vou_vender*(1-corretoraLeilao.corretagem_limitada) >= (1+corretoraZeragem.corretagem_mercado) * preco_de_zeragem):
                
                logging.info('leilao de compra aberta para moeda {} no preço de venda {} e preço de zeragem {}'.format(ativo,round(preco_que_vou_vender,2),round(preco_de_zeragem,2)))                                
                #existe oportunidade de leilao, vou checar saldo
                corretoraLeilao.atualizar_saldo()
                corretoraZeragem.atualizar_saldo()

                # Gostaria de vender no leilão pelo 1/4 do que eu tenho de saldo em crypto
                gostaria_de_vender = corretoraLeilao.saldo[ativo] / 4
                maximo_que_consigo_zerar = corretoraZeragem.saldo['brl'] / (qtd_de_moedas*preco_de_zeragem)
                qtdNegociada = min(gostaria_de_vender,maximo_que_consigo_zerar)

                # Truncando as casas decimais conforme regra da corretora de maior liquidez
                if ativo =='xrp':
                    qtdNegociada = math.trunc(qtdNegociada*100)/100 #trunca na segunda
                else:
                    qtdNegociada = math.trunc(qtdNegociada*1000000)/1000000 #trunca na sexta 

                # Nao pode ter saldo na mercado de menos de um real
                if (qtdNegociada*preco_que_vou_vender > Util.retorna_menor_valor_compra(ativo) and corretoraZeragem.saldo['brl'] > Util.retorna_menor_valor_compra(ativo)):
                    
                    
                    if executarOrdens and qtdNegociada > Util.retorna_menor_quantidade_venda(ativo):
                        
                        logging.info('Leilão compra vai enviar ordem de venda de {} limitada a {}'.format(ativo,preco_que_vou_vender))
                        corretoraLeilao.ordem.preco_enviado = preco_que_vou_vender
                        corretoraLeilao.ordem.quantidade_enviada = qtdNegociada
                        corretoraLeilao.ordem.tipo_ordem = 'limited'
                        retorno_venda_corretora_leilao = corretoraLeilao.enviar_ordem_venda(corretoraLeilao.ordem,ativo) 
                else:
                    financeiro_venda = qtdNegociada*preco_que_vou_vender
                    financeiro_venda_minimo = Util.retorna_menor_valor_compra(ativo)
                    zeragem_compra = corretoraZeragem.saldo['brl']
                    zeragem_compra_minimo = Util.retorna_menor_valor_compra(ativo)
                    logging.info('leilao de compra nao executado para moeda {}, pois o financeiro venda: {} < que financeiro venda minimo: {}, ou zeragem compra: {} < zeragem compra minimo: {}'.format(ativo,round(financeiro_venda,2),round(financeiro_venda_minimo,2),round(zeragem_compra,2),round(zeragem_compra_minimo,2)))   
            else:
                logging.info('leilao compra de {} nao vale a pena, (1+corretagem)*{} é menor que (1-corretagem)*{}'.format(ativo,preco_que_vou_vender,preco_de_zeragem))

        except Exception as erro:
                msg_erro = Util.retorna_erros_objeto_exception('Erro na estratégia de leilão, método: compra. Msg Corretora:', erro)
                raise Exception(msg_erro)

        return retorno_venda_corretora_leilao

    def envia_venda_limitada(corretoraLeilao:Corretora, corretoraZeragem:Corretora, ativo, executarOrdens = False):

        retorno_compra_corretora_leilao = Ordem()

        try:
            qtd_de_moedas = len(Util.obter_lista_de_moedas())

            #carrego os books de ordem mais recentes, a partir daqui precisamos ser rapidos!!! é a hora do show!!
            corretoraLeilao.book.obter_ordem_book_por_indice(ativo,'brl',0,True)
            corretoraZeragem.book.obter_ordem_book_por_indice(ativo,'brl',0,True)

            preco_que_vou_comprar = corretoraLeilao.book.preco_venda+0.01 #primeiro no book de ordens + 1 centavo
            preco_de_zeragem = corretoraZeragem.book.preco_venda # zeragem no primeiro book de ordens

            # Valida se existe oportunidade de leilão
            if preco_que_vou_comprar*(1+corretoraLeilao.corretagem_limitada) <= preco_de_zeragem*(1-corretoraZeragem.corretagem_mercado):
                logging.info('leilao de venda aberta para moeda {} no preço de compra {} e preço de zeragem {}'.format(ativo,round(preco_que_vou_comprar,2),round(preco_de_zeragem,2)))                   
                #existe oportunidade de leilao, vou checar saldo
                corretoraLeilao.atualizar_saldo()
                corretoraZeragem.atualizar_saldo()

                gostaria_de_comprar = corretoraLeilao.saldo['brl'] / (qtd_de_moedas * preco_que_vou_comprar)
                maximo_que_consigo_zerar = corretoraZeragem.saldo[ativo] / 4
                
                # Mínimo entre o que eu gostaria de comprar com o máximo que consigo zerar na outra ponta
                qtdNegociada = min(gostaria_de_comprar,maximo_que_consigo_zerar)

                # Truncando as casas decimais conforme regra da corretora de maior liquidez
                if ativo =='xrp':
                    qtdNegociada = math.trunc(qtdNegociada*100)/100#trunca na segunda
                else:
                    qtdNegociada = math.trunc(qtdNegociada*1000000)/1000000#trunca na sexta 
                
                # Se quantidade negociada maior que a quantidade mínima permitida de venda
                if qtdNegociada > Util.retorna_menor_quantidade_venda(ativo):

                    if executarOrdens:

                        logging.info('leilao venda de vai enviar ordem de venda de {} limitada a {}'.format(ativo,preco_que_vou_comprar))
                        corretoraLeilao.ordem.preco_enviado = preco_que_vou_comprar
                        corretoraLeilao.ordem.quantidade_enviada = qtdNegociada
                        corretoraLeilao.ordem.tipo_ordem = 'limited'    
                        retorno_compra_corretora_leilao = corretoraLeilao.enviar_ordem_compra(corretoraLeilao.ordem,ativo)
                else:
                    quantidade_compra = qtdNegociada
                    quantidade_venda_minimo = Util.retorna_menor_quantidade_venda(ativo)
                    logging.info('leilao de venda nao executado para moeda {} pois nao tem quantidades disponiveis suficientes para venda: {}<{}'.format(ativo,quantidade_compra,quantidade_venda_minimo)) 
            else:
                logging.info('leilao venda de {} nao vale a pena, {} é maior que 0.99*{}'.format(ativo,preco_que_vou_comprar,preco_de_zeragem))
        except Exception as erro:
                msg_erro = Util.retorna_erros_objeto_exception('o, método: venda. Msg Corretora:', erro)
                raise Exception(msg_erro)
        
        return retorno_compra_corretora_leilao

    def cancela_ordens_de_compra_e_zera(corretoraLeilao:Corretora, corretoraZeragem:Corretora, ativo, executarOrdens, ordem_leilao_compra):

        retorno_compra = Ordem()
        cancelou = False

        try:
        
            ordem = corretoraLeilao.obter_ordem_por_id(ativo,ordem_leilao_compra) if  ordem_leilao_compra.id != 0 else Ordem()
            ordem_leilao_compra.quantidade_executada = ordem.quantidade_executada

            if ordem.status == corretoraLeilao.descricao_status_executado and ordem_leilao_compra.id == False: # verifica se a ordem foi executada totalmente (Nesse caso o ID = False)
                
                logging.info('leilao compra vai zerar ordem executada completamente {} de {} na outra corretora'.format(ordem_leilao_compra.id,ativo))
                
                if corretoraZeragem.nome == 'MercadoBitcoin':
                    corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada #quando vc compra na mercado, ele compra um pouco a mais e pega pra ele de corretagem, é só vender a mesma qtd
                else:
                    corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada/(1-corretoraZeragem.corretagem_mercado)
                
                corretoraZeragem.ordem.tipo_ordem = 'market'
                retorno_compra = corretoraZeragem.enviar_ordem_compra(corretoraZeragem.ordem,ativo)
                
            elif ordem_leilao_compra.id != 0:
                
                #carrego os books de ordem mais recentes, a partir daqui precisamos ser rapidos!!! é a hora do show!!
                corretoraZeragem.atualizar_saldo()
                corretoraLeilao.book.obter_ordem_book_por_indice(ativo,'brl',0,True)
                corretoraZeragem.book.obter_ordem_book_por_indice(ativo,'brl',0,True)
                
                if executarOrdens and ordem.quantidade_executada * corretoraLeilao.book.preco_compra > Util.retorna_menor_valor_compra(ativo): #mais de xxx reais executado
                                   
                    logging.info('leilao compra vai cancelar ordem {} de {} pq fui executado mais que o valor minimo'.format(ordem_leilao_compra.id,ativo))
                    cancelou =corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_compra.id)
                
                    # Zera o risco na outra corretora com uma operação à mercado
                    if corretoraZeragem.nome == 'MercadoBitcoin':
                        corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada #quando vc compra na mercado, ele compra um pouco a mais e pega pra ele de corretagem, é só vender a mesma qtd
                    else:
                        corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada/(1-corretoraZeragem.corretagem_mercado)
                    
                    corretoraZeragem.ordem.preco_enviado = float(ordem.preco_executado)
                    corretoraZeragem.ordem.tipo_ordem = 'market'
                    retorno_compra = corretoraZeragem.enviar_ordem_compra(corretoraZeragem.ordem,ativo)
                
                elif (ordem_leilao_compra.preco_enviado != corretoraLeilao.book.preco_compra):
                    
                    logging.info('leilao compra vai cancelar ordem {} de {} pq nao sou o primeiro da fila na {}'.format(ordem_leilao_compra.id,ativo,corretoraLeilao.nome))
                    cancelou = corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_compra.id)
                    
                elif (corretoraZeragem.saldo['brl'] < ordem_leilao_compra.quantidade_enviada*ordem_leilao_compra.preco_enviado):
                    
                    logging.info('leilao compra vai cancelar ordem {} de {} pq meu saldo brl {} nao consegue comprar {}'.format(ordem_leilao_compra.id,ativo,corretoraZeragem.saldo['brl'],ordem_leilao_compra.quantidade_enviada*ordem_leilao_compra.preco_enviado))
                    cancelou =corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_compra.id)
                    
                elif (ordem_leilao_compra.preco_enviado*(1-corretoraLeilao.corretagem_limitada) < (1+corretoraZeragem.corretagem_mercado) * corretoraZeragem.book.preco_compra):
                                        
                    logging.info('leilao compra vai cancelar ordem {} de {} pq o pnl esta dando negativo'.format(ordem_leilao_compra.id,ativo))
                    cancelou =corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_compra.id)
                    
                                
        except Exception as erro:
            msg_erro = Util.retorna_erros_objeto_exception('Erro na estratégia de leilão, método: cancela_ordens_e_compra_na_mercado. (Ativo: {} | Quant: {})'.format(ativo, corretoraZeragem.ordem.quantidade_enviada), erro)
            raise Exception(msg_erro)

        return retorno_compra, cancelou

    def cancela_ordens_de_venda_e_zera(corretoraLeilao:Corretora, corretoraZeragem:Corretora, ativo, executarOrdens, ordem_leilao_venda):

        retorno_venda = Ordem()
        cancelou = False

        try:
    
            ordem = corretoraLeilao.obter_ordem_por_id(ativo,ordem_leilao_venda) if  ordem_leilao_venda.id != 0 else Ordem()
            ordem_leilao_venda.quantidade_executada = ordem.quantidade_executada

            if ordem.status == corretoraLeilao.descricao_status_executado and ordem_leilao_venda.id == False:

                corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada*(1-corretoraLeilao.corretagem_limitada)
                corretoraZeragem.ordem.tipo_ordem = 'market'
                retorno_venda = corretoraZeragem.enviar_ordem_venda(corretoraZeragem.ordem,ativo)
                logging.info('quantidade_enviada {} quantidade_executada_leilao {} Taxa_desconto {}'.format(corretoraZeragem.ordem.quantidade_enviada,ordem_leilao_venda.quantidade_executada,corretoraLeilao.corretagem_limitada))

            elif ordem_leilao_venda.id != 0:
                
                #carrego os books de ordem mais recentes, a partir daqui precisamos ser rapidos!!! é a hora do show!!
                corretoraZeragem.atualizar_saldo()
                corretoraLeilao.book.obter_ordem_book_por_indice(ativo,'brl',0,True)
                corretoraZeragem.book.obter_ordem_book_por_indice(ativo,'brl',0,True)           

                if executarOrdens and ordem.quantidade_executada > Util.retorna_menor_quantidade_venda(ativo): 

                    logging.info('leilao venda vai cancelar ordem {} de {} pq fui executado mais que o valor minimo'.format(ordem_leilao_venda.id,ativo,Util.retorna_menor_quantidade_venda(ativo)))
                    cancelou = corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_venda.id)
                
                    logging.info('leilao venda vai zerar na {} ordem executada {} de {}'.format(corretoraZeragem.nome,ordem_leilao_venda.id,ativo))
                    corretoraZeragem.ordem.quantidade_enviada = ordem.quantidade_executada*(1-corretoraLeilao.corretagem_limitada)             
                    corretoraZeragem.ordem.tipo_ordem = 'market'
                    retorno_venda = corretoraZeragem.enviar_ordem_venda(corretoraZeragem.ordem,ativo)
                    logging.info('quantidade_enviada {} quantidade_executada_leilao {} Taxa_desconto {}'.format(corretoraZeragem.ordem.quantidade_enviada,ordem_leilao_venda.quantidade_executada,corretoraLeilao.corretagem_limitada))
                
                elif (ordem_leilao_venda.preco_enviado != corretoraLeilao.book.preco_venda):
                    
                    logging.info('leilao venda vai cancelar ordem {} de {} pq nao sou o primeiro da fila na {}'.format(ordem_leilao_venda.id,ativo,corretoraLeilao.nome))
                    cancelou = corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_venda.id)
                    
                elif (corretoraZeragem.saldo[ativo] < ordem_leilao_venda.quantidade_enviada):
                    
                    logging.info('leilao venda vai cancelar ordem {} de {} pq meu saldo em cripto {} é menor que oq eu queria vender {}'.format(ordem_leilao_venda.id,ativo,corretoraZeragem.saldo[ativo],ordem_leilao_venda.quantidade_enviada))
                    cancelou = corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_venda.id)
                    
                elif (ordem_leilao_venda.preco_enviado*(1+corretoraLeilao.corretagem_limitada) >  corretoraZeragem.book.preco_venda*(1-corretoraZeragem.corretagem_mercado)):
                    
                    logging.info('leilao venda vai cancelar ordem {} de {} pq o pnl esta dando negativo'.format(ordem_leilao_venda.id,ativo))
                    cancelou = corretoraLeilao.cancelar_ordem(ativo,ordem_leilao_venda.id)
                    
                
        except Exception as erro:
            msg_erro = Util.retorna_erros_objeto_exception('Erro na estratégia de leilão, método: cancela_ordens_e_vende_na_mercado. (Ativo: {} | Quant: {})'.format(ativo, corretoraZeragem.ordem.quantidade_enviada), erro)
            raise Exception(msg_erro)
        
        return retorno_venda,cancelou


if __name__ == "__main__":

    import requests
    
    from datetime import datetime, timedelta
    from caixa import Caixa
    from leilao import Leilao
    
    #inicializa arquivo de logs, no arquivo vai a porra toda, mas no console só os warning ou acima
    logging.basicConfig(filename='leilao.log', level=logging.INFO,
                        format='[%(asctime)s][%(levelname)s][%(message)s]')
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)

    #essa parte executa apenas uma vez
    lista_de_moedas = Util.obter_lista_de_moedas()
    corretora_mais_liquida = Util.obter_corretora_de_maior_liquidez()
    corretora_menos_liquida = Util.obter_corretora_de_menor_liquidez()

    retorno_ordem_leilao_compra = Ordem()
    retorno_ordem_leilao_venda = Ordem()

    dict_leilao_compra = {}
    dict_leilao_venda = {}

    for moeda in lista_de_moedas:
        dict_leilao_compra[moeda]={}
        dict_leilao_venda[moeda]={}
        dict_leilao_compra[moeda]['ordem'] = Ordem()
        dict_leilao_venda[moeda]['ordem'] = Ordem()
        dict_leilao_compra[moeda]['zeragem'] = Ordem()
        dict_leilao_venda[moeda]['zeragem'] = Ordem()
        dict_leilao_compra[moeda]['foi_cancelado'] = False
        dict_leilao_venda[moeda]['foi_cancelado'] = False

    CorretoraMaisLiquida = Corretora(corretora_mais_liquida)
    CorretoraMenosLiquida = Corretora(corretora_menos_liquida)

    Caixa.atualiza_saldo_inicial(lista_de_moedas,CorretoraMaisLiquida,CorretoraMenosLiquida)
    
    while True:

        for moeda in lista_de_moedas:
            try:
                # Instancia das corretoras
                CorretoraMaisLiquida = Corretora(corretora_mais_liquida)
                CorretoraMenosLiquida = Corretora(corretora_menos_liquida)

                #verifica se fui executado e se necessario cancelar ordens abertas            
                dict_leilao_compra[moeda]['zeragem'], dict_leilao_compra[moeda]['foi_cancelado'] = Leilao.cancela_ordens_de_compra_e_zera(CorretoraMenosLiquida, CorretoraMaisLiquida, moeda, True, dict_leilao_compra[moeda]['ordem'])
                
                # Se Id diferente de zero, significa que operou leilão (fui executado)
                if dict_leilao_compra[moeda]['zeragem'].id != 0:
                    
                    comprei_a = round(dict_leilao_compra[moeda]['zeragem'].preco_executado,2)
                    vendi_a = round(dict_leilao_compra[moeda]['ordem'].preco_enviado,2)
                    quantidade = round(dict_leilao_compra[moeda]['zeragem'].quantidade_executada,4)

                    pnl = round((vendi_a * (1-CorretoraMenosLiquida.corretagem_limitada) - comprei_a * (1+CorretoraMaisLiquida.corretagem_mercado)) * quantidade,2)

                    logging.warning('operou leilao de compra de {}! + {}brl de pnl (compra de {}{} @{} na {} e venda a @{} na {})'.format(moeda,pnl,quantidade,moeda,comprei_a,CorretoraMaisLiquida.nome,vendi_a,CorretoraMenosLiquida.nome))
                    
                    quantidade_executada_compra = dict_leilao_compra[moeda]['zeragem'].quantidade_executada
                    quantidade_executada_venda = dict_leilao_compra[moeda]['ordem'].quantidade_executada

                    Util.adicionar_linha_em_operacoes(moeda,CorretoraMaisLiquida.nome,comprei_a,quantidade_executada_compra,CorretoraMenosLiquida.nome,vendi_a,quantidade_executada_venda,pnl,'LEILAO',str(datetime.now()))
                    
                    dict_leilao_compra[moeda]['ordem'] = Ordem() #reinicia as ordens
                    dict_leilao_compra[moeda]['zeragem'] = Ordem() #reinicia as ordens

                elif dict_leilao_compra[moeda]['ordem'].id == 0 or dict_leilao_compra[moeda]['foi_cancelado']: #se não ha ordens abertas ou se ordens foram canceladas, envia uma nova
                    #logging.info('leilao compra vai enviar nova ordem pois id:{} é zero ou foi cancelado: {}'.format(dict_leilao_compra[moeda]['ordem'].id,dict_leilao_compra[moeda]['foi_cancelado']))
                    dict_leilao_compra[moeda]['ordem']  = Leilao.envia_compra_limitada(CorretoraMenosLiquida, CorretoraMaisLiquida, moeda, True)
                
                # Instancia das corretoras
                CorretoraMaisLiquida = Corretora(corretora_mais_liquida)
                CorretoraMenosLiquida = Corretora(corretora_menos_liquida)

                dict_leilao_venda[moeda]['zeragem'], dict_leilao_venda[moeda]['foi_cancelado'] = Leilao.cancela_ordens_de_venda_e_zera(CorretoraMenosLiquida, CorretoraMaisLiquida, moeda, True, dict_leilao_venda[moeda]['ordem'])
                
                # Se Id diferente de zero, significa que operou leilão (fui executado)
                if  dict_leilao_venda[moeda]['zeragem'].id != 0:

                    vendi_a = round(dict_leilao_venda[moeda]['zeragem'].preco_executado,2)
                    comprei_a = round(dict_leilao_venda[moeda]['ordem'].preco_enviado,2)
                    quantidade = round(dict_leilao_venda[moeda]['zeragem'].quantidade_executada,4)

                    pnl = round(((vendi_a*(1-CorretoraMaisLiquida.corretagem_mercado))-(comprei_a*(1+CorretoraMenosLiquida.corretagem_limitada))) * quantidade,2)

                    logging.warning('operou leilao de venda de {}! + {}brl de pnl (venda de {}{} @{} na {} e compra a @{} na {})'.format(moeda,pnl,quantidade,moeda,vendi_a,CorretoraMaisLiquida.nome,comprei_a,CorretoraMenosLiquida.nome))
                    
                    quantidade_executada_compra = dict_leilao_venda[moeda]['ordem'].quantidade_executada
                    quantidade_executada_venda = dict_leilao_venda[moeda]['zeragem'].quantidade_executada

                    Util.adicionar_linha_em_operacoes(moeda,CorretoraMenosLiquida.nome,comprei_a,quantidade_executada_compra,CorretoraMaisLiquida.nome,vendi_a,quantidade_executada_venda,pnl,'LEILAO',str(datetime.now()))

                    dict_leilao_venda[moeda]['ordem'] = Ordem() #reinicia as ordens  
                    dict_leilao_venda[moeda]['zeragem'] = Ordem() #reinicia as ordens 

                elif dict_leilao_venda[moeda]['ordem'].id == 0 or  dict_leilao_venda[moeda]['foi_cancelado']:#se não ha ordens abertas ou se ordens foram canceladas, envia uma nova
                    dict_leilao_venda[moeda]['ordem'] = Leilao.envia_venda_limitada(CorretoraMenosLiquida, CorretoraMaisLiquida, moeda, True)
                                    
            except Exception as erro:        
                logging.error(erro) 
            




