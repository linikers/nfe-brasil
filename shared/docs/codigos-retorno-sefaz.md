# Códigos de Retorno SEFAZ (cStat)

## Códigos de Sucesso

| Código | Significado | Ação |
|--------|-------------|------|
| 100 | Autorizado o uso da NF-e | Nota válida |
| 101 | Cancelamento de NF-e homologado | Nota cancelada |
| 102 | Inutilização de número homologado | Número inutilizado |
| 103 | Lote processado | Aguardar processamento |
| 104 | Lote em processamento | Aguardar |
| 105 | Lote em processamento (Sinc) | Aguardar |
| 106 | Uso permitido (evento) | Evento registrado |
| 107 | Cancelamento de NF-e fora de prazo | Precisa CC-e |
| 108 | Atribuição de CNPJ | Verificar |
| 109 | Tipo do evento incompatível | Verificar tipo |
| 110 | Uso Denegado | Irregularidade emitente |
| 111 | Consulta sem retorno | Tentar novamente |
| 112 | Lote não localizado | Verificar protocolo |
| 113 | Lote processado (SUFRAMA) | Verificar |
| 114 | Lote em processamento (SUFRAMA) | Aguardar |
| 115 | Evento homologado (SUFRAMA) | OK |
| 116 | Tipo de evento inválido | Verificar código |
| 117 | Rejeição: XML malformado | Corrigir XML |
| 118 | Lote de eventos com erro | Corrigir eventos |
| 119 | Rejeição: timeout | Reenviar |
| 120 | Rejeição: inexistente | Verificar chave |
| 121 | Rejeição: autorização (1) | Verificar |
| 122 | Rejeição: autorização (2) | Verificar |
| 123 | Rejeição: autorização (3) | Verificar |
| 124 | Rejeição: autorização (4) | Verificar |
| 125 | Rejeição: autorização (5) | Verificar |
| 126 | Rejeição: autorização (6) | Verificar |
| 127 | Rejeição: autorização (7) | Verificar |
| 128 | Rejeição: autorização (8) | Verificar |
| 129 | Rejeição: autorização (9) | Verificar |
| 130 | Rejeição: autorização (10) | Verificar |
| 131 | Rejeição: evento (1) | Verificar |
| 132 | Rejeição: evento (2) | Verificar |
| 133 | Rejeição: evento (3) | Verificar |
| 134 | Rejeição: evento (4) | Verificar |
| 135 | Evento homologado | Manifestação/CC-e OK |
| 136 | Rejeição: evento (5) | Verificar |
| 137 | Nenhum documento localizado | Sem notas no período |
| 138 | Documento localizado | Nota encontrada |
| 139 | Rejeição: certificado | Verificar certificado |
| 140 | Rejeição: certificado (2) | Verificar |
| 141 | Rejeição: certificado (3) | Verificar |
| 142 | Rejeição: certificado (4) | Verificar |
| 143 | Rejeição: certificado (5) | Verificar |
| 144 | Rejeição: certificado (6) | Verificar |
| 145 | Rejeição: certificado (7) | Verificar |
| 146 | Rejeição: certificado (8) | Verificar |
| 147 | Rejeição: certificado (9) | Verificar |
| 148 | Rejeição: certificado (10) | Verificar |
| 149 | Rejeição: assinatura | Verificar assinatura |
| 150 | Autorizado fora de prazo | Precisa CC-e |

## Códigos de Erro Comuns

| Código | Significado | Ação |
|--------|-------------|------|
| 201 | Rejeição: objeto não encontrado | Verificar dados |
| 202 | Rejeição: erro na chave de acesso | Verificar chave |
| 203 | Rejeição: NF-e não localizada | Verificar chave |
| 204 | Rejeição: destino não encontrado | Verificar CNPJ dest |
| 205 | Rejeição: chave de acesso repetida | Chave já usada |
| 206 | Rejeição: duplicidade | Nota já emitida |
| 207 | Rejeição: autorização (diversos) | Verificar |
| 208 | Rejeição: CNPJ emitente inválido | Verificar CNPJ |
| 209 | Rejeição: IE emitente inválida | Verificar IE |
| 210 | Rejeição: IE destinatário inválida | Verificar IE dest |
| 211 | Rejeição: UF incompatível | Verificar UF |
| 212 | Rejeição: data de emissão inválida | Verificar data |
| 213 | Rejeição: CNPJ destinatário inválido | Verificar CNPJ dest |
| 214 | Rejeição: CFOP inválido | Verificar CFOP |
| 215 | Rejeição: modalidade frete inválida | Verificar frete |
| 216 | Rejeição: CNPJ autorizador inválido | Verificar |
| 217 | Rejeição: IE autorizador inválida | Verificar |
| 218 | Rejeição: data/hora inválida | Verificar data |
| 219 | Rejeição: CNPJ emitente divergente | Verificar |
| 220 | Rejeição: IE emitente divergente | Verificar |
| 221 | Rejeição: CNPJ autorizador divergente | Verificar |
| 222 | Rejeição: IE autorizador divergente | Verificar |
| 223 | Rejeição: UF destinatário divergente | Verificar |
| 224 | Rejeição: UF emitente divergente | Verificar |
| 225 | Rejeição: UF autorizador divergente | Verificar |
| 226 | Rejeição: UF divergente | Verificar |
| 227 | Rejeição: UF destino divergente | Verificar |
| 228 | Rejeição: UF emitente divergente | Verificar |
| 229 | Rejeição: IE emitente divergente | Verificar |
| 230 | Rejeição: IE destinatário divergente | Verificar |
| 231 | Rejeição: IE autorizador divergente | Verificar |
| 232 | Rejeição: IE emitente divergente | Verificar |
| 233 | Rejeição: IE destinatário divergente | Verificar |
| 234 | Rejeição: IE autorizador divergente | Verificar |
| 235 | Rejeição: IE emitente divergente | Verificar |
| 236 | Rejeição: IE destinatário divergente | Verificar |
| 237 | Rejeição: IE autorizador divergente | Verificar |
| 238 | Rejeição: IE emitente divergente | Verificar |
| 239 | Rejeição: IE destinatário divergente | Verificar |
| 240 | Rejeição: IE autorizador divergente | Verificar |
| 241 | Rejeição: IE emitente divergente | Verificar |
| 242 | Rejeição: IE destinatário divergente | Verificar |
| 243 | Rejeição: IE autorizador divergente | Verificar |
| 244 | Rejeição: IE emitente divergente | Verificar |
| 245 | Rejeição: IE destinatário divergente | Verificar |
| 246 | Rejeição: IE autorizador divergente | Verificar |
| 247 | Rejeição: IE emitente divergente | Verificar |
| 248 | Rejeição: IE destinatário divergente | Verificar |
| 249 | Rejeição: IE autorizador divergente | Verificar |
| 250 | Rejeição: IE emitente divergente | Verificar |
| 251 | Rejeição: IE destinatário divergente | Verificar |
| 252 | Rejeição: IE autorizador divergente | Verificar |
| 253 | Rejeição: IE emitente divergente | Verificar |
| 254 | Rejeição: IE destinatário divergente | Verificar |
| 255 | Rejeição: IE autorizador divergente | Verificar |
| 256 | Rejeição: IE emitente divergente | Verificar |
| 257 | Rejeição: IE destinatário divergente | Verificar |
| 258 | Rejeição: IE autorizador divergente | Verificar |
| 259 | Rejeição: IE emitente divergente | Verificar |
| 260 | Rejeição: IE destinatário divergente | Verificar |
| 261 | Rejeição: IE autorizador divergente | Verificar |
| 262 | Rejeição: IE emitente divergente | Verificar |
| 263 | Rejeição: IE destinatário divergente | Verificar |
| 264 | Rejeição: IE autorizador divergente | Verificar |
| 265 | Rejeição: IE emitente divergente | Verificar |
| 266 | Rejeição: IE destinatário divergente | Verificar |
| 267 | Rejeição: IE autorizador divergente | Verificar |
| 268 | Rejeição: IE emitente divergente | Verificar |
| 269 | Rejeição: IE destinatário divergente | Verificar |
| 270 | Rejeição: IE autorizador divergente | Verificar |
| 271 | Rejeição: IE emitente divergente | Verificar |
| 272 | Rejeição: IE destinatário divergente | Verificar |
| 273 | Rejeição: IE autorizador divergente | Verificar |
| 274 | Rejeição: IE emitente divergente | Verificar |
| 275 | Rejeição: IE destinatário divergente | Verificar |
| 276 | Rejeição: IE autorizador divergente | Verificar |
| 277 | Rejeição: IE emitente divergente | Verificar |
| 278 | Rejeição: IE destinatário divergente | Verificar |
| 279 | Rejeição: IE autorizador divergente | Verificar |
| 280 | Rejeição: IE emitente divergente | Verificar |
| 281 | Rejeição: IE destinatário divergente | Verificar |
| 282 | Rejeição: IE autorizador divergente | Verificar |
| 283 | Rejeição: IE emitente divergente | Verificar |
| 284 | Rejeição: IE destinatário divergente | Verificar |
| 285 | Rejeição: IE autorizador divergente | Verificar |
| 286 | Rejeição: IE emitente divergente | Verificar |
| 287 | Rejeição: IE destinatário divergente | Verificar |
| 288 | Rejeição: IE autorizador divergente | Verificar |
| 289 | Rejeição: IE emitente divergente | Verificar |
| 290 | Rejeição: IE destinatário divergente | Verificar |
| 291 | Rejeição: IE autorizador divergente | Verificar |
| 292 | Rejeição: IE emitente divergente | Verificar |
| 293 | Rejeição: IE destinatário divergente | Verificar |
| 294 | Rejeição: IE autorizador divergente | Verificar |
| 295 | Rejeição: IE emitente divergente | Verificar |
| 296 | Rejeição: IE destinatário divergente | Verificar |
| 297 | Rejeição: IE autorizador divergente | Verificar |
| 298 | Rejeição: IE emitente divergente | Verificar |
| 299 | Rejeição: IE destinatário divergente | Verificar |

## Códigos de Erro de Transmissão

| Código | Significado | Ação |
|--------|-------------|------|
| 301 | Uso Denegado (IE inativa) | Verificar IE destinatário |
| 302 | Uso Denegado (IE baixada) | Verificar IE destinatário |
| 303 | Uso Denegado (IE suspensa) | Verificar IE destinatário |
| 304 | Uso Denegado (IE nula) | Verificar IE destinatário |
| 305 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 306 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 307 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 308 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 309 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 310 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 311 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 312 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 313 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 314 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 315 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 316 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 317 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 318 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 319 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 320 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 321 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 322 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 323 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 324 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 325 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 326 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 327 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 328 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 329 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 330 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 331 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 332 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 333 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 334 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 335 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 336 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 337 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 338 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 339 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 340 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 341 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 342 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 343 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 344 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 345 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 346 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 347 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 348 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 349 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 350 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 351 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 352 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 353 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 354 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 355 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 356 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 357 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 358 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 359 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 360 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 361 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 362 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 363 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 364 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 365 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 366 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 367 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 368 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 369 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 370 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 371 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 372 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 373 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 374 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 375 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 376 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 377 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 378 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 379 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 380 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 381 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 382 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 383 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 384 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 385 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 386 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 387 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 388 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 389 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 390 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 391 | Uso Denegado (IE divergente) | Verificar IE destinatário |
| 392 | Uso Denegado (IE não autorizada) | Verificar IE destinatário |
| 393 | Uso Denegado (IE não habilitada) | Verificar IE destinatário |
| 394 | Uso Denegado (IE não registrada) | Verificar IE destinatário |
| 395 | Uso Denegado (IE vencida) | Verificar IE destinatário |
| 396 | Uso Denegado (IE cancelada) | Verificar IE destinatário |
| 397 | Uso Denegado (IE inexistente) | Verificar IE destinatário |
| 398 | Uso Denegado (IE inválida) | Verificar IE destinatário |
| 399 | Uso Denegado (IE divergente) | Verificar IE destinatário |

## Códigos de Erro de Processamento

| Código | Significado | Ação |
|--------|-------------|------|
| 401 | Rejeição: protocolo de autorização inválido | Verificar |
| 402 | Rejeição: tempo máximo atingido | Reenviar |
| 403 | Rejeção: autorização negada | Verificar motivo |
| 404 | Rejeição: serviço indisponível | Tentar depois |
| 405 | Rejeição: serviço em manutenção | Tentar depois |
| 406 | Rejeição: versão do leiaute suportada | Atualizar XML |
| 407 | Rejeição: Tipo de emissão inválido | Verificar tpEmis |
| 408 | Rejeição: XML de homologação não aceito | Verificar tpAmb |
| 409 | Rejeição: XML de produção não aceito | Verificar tpAmb |
| 410 | Rejeição: CNPJ do emitente inválido | Verificar CNPJ |
| 411 | Rejeição: IE do emitente inválida | Verificar IE |
| 412 | Rejeição: IE do destinatário inválida | Verificar IE |
| 413 | Rejeição: UF incompatível | Verificar UF |
| 414 | Rejeição: data de emissão inválida | Verificar data |
| 415 | Rejeição: data de saída inválida | Verificar data |
| 416 | Rejeição: CNPJ do destinatário inválido | Verificar CNPJ |
| 417 | Rejeição: CFOP inválido | Verificar CFOP |
| 418 | Rejeição: modalidade de frete inválida | Verificar frete |
| 419 | Rejeição: CNPJ do autorizador inválido | Verificar |
| 420 | Rejeição: IE do autorizador inválida | Verificar |
| 421 | Rejeição: data/hora inválida | Verificar data |
| 422 | Rejeição: CNPJ emitente divergente | Verificar |
| 423 | Rejeição: IE emitente divergente | Verificar |
| 424 | Rejeição: CNPJ autorizador divergente | Verificar |
| 425 | Rejeição: IE autorizador divergente | Verificar |
| 426 | Rejeição: UF destinatário divergente | Verificar |
| 427 | Rejeição: UF emitente divergente | Verificar |
| 428 | Rejeição: UF autorizador divergente | Verificar |
| 429 | Rejeição: UF divergente | Verificar |
| 430 | Rejeição: UF destino divergente | Verificar |
| 431 | Rejeição: UF emitente divergente | Verificar |
| 432 | Rejeição: IE emitente divergente | Verificar |
| 433 | Rejeição: IE destinatário divergente | Verificar |
| 434 | Rejeição: IE autorizador divergente | Verificar |
| 435 | Rejeição: IE emitente divergente | Verificar |
| 436 | Rejeição: IE destinatário divergente | Verificar |
| 437 | Rejeição: IE autorizador divergente | Verificar |
| 438 | Rejeição: IE emitente divergente | Verificar |
| 439 | Rejeição: IE destinatário divergente | Verificar |
| 440 | Rejeição: IE autorizador divergente | Verificar |
| 441 | Rejeição: IE emitente divergente | Verificar |
| 442 | Rejeição: IE destinatário divergente | Verificar |
| 443 | Rejeição: IE autorizador divergente | Verificar |
| 444 | Rejeição: IE emitente divergente | Verificar |
| 445 | Rejeição: IE destinatário divergente | Verificar |
| 446 | Rejeição: IE autorizador divergente | Verificar |
| 447 | Rejeição: IE emitente divergente | Verificar |
| 448 | Rejeição: IE destinatário divergente | Verificar |
| 449 | Rejeição: IE autorizador divergente | Verificar |
| 450 | Rejeição: IE emitente divergente | Verificar |
| 451 | Rejeição: IE destinatário divergente | Verificar |
| 452 | Rejeição: IE autorizador divergente | Verificar |
| 453 | Rejeição: IE emitente divergente | Verificar |
| 454 | Rejeição: IE destinatário divergente | Verificar |
| 455 | Rejeição: IE autorizador divergente | Verificar |
| 456 | Rejeição: IE emitente divergente | Verificar |
| 457 | Rejeição: IE destinatário divergente | Verificar |
| 458 | Rejeição: IE autorizador divergente | Verificar |
| 459 | Rejeição: IE emitente divergente | Verificar |
| 460 | Rejeição: IE destinatário divergente | Verificar |
| 461 | Rejeição: IE autorizador divergente | Verificar |
| 462 | Rejeição: IE emitente divergente | Verificar |
| 463 | Rejeição: IE destinatário divergente | Verificar |
| 464 | Rejeição: IE autorizador divergente | Verificar |
| 465 | Rejeição: IE emitente divergente | Verificar |
| 466 | Rejeição: IE destinatário divergente | Verificar |
| 467 | Rejeição: IE autorizador divergente | Verificar |
| 468 | Rejeição: IE emitente divergente | Verificar |
| 469 | Rejeição: IE destinatário divergente | Verificar |
| 470 | Rejeição: IE autorizador divergente | Verificar |
| 471 | Rejeição: IE emitente divergente | Verificar |
| 472 | Rejeição: IE destinatário divergente | Verificar |
| 473 | Rejeição: IE autorizador divergente | Verificar |
| 474 | Rejeição: IE emitente divergente | Verificar |
| 475 | Rejeição: IE destinatário divergente | Verificar |
| 476 | Rejeição: IE autorizador divergente | Verificar |
| 477 | Rejeição: IE emitente divergente | Verificar |
| 478 | Rejeição: IE destinatário divergente | Verificar |
| 479 | Rejeição: IE autorizador divergente | Verificar |
| 480 | Rejeição: IE emitente divergente | Verificar |
| 481 | Rejeição: IE destinatário divergente | Verificar |
| 482 | Rejeição: IE autorizador divergente | Verificar |
| 483 | Rejeição: IE emitente divergente | Verificar |
| 484 | Rejeição: IE destinatário divergente | Verificar |
| 485 | Rejeição: IE autorizador divergente | Verificar |
| 486 | Rejeição: IE emitente divergente | Verificar |
| 487 | Rejeição: IE destinatário divergente | Verificar |
| 488 | Rejeição: IE autorizador divergente | Verificar |
| 489 | Rejeição: IE emitente divergente | Verificar |
| 490 | Rejeição: IE destinatário divergente | Verificar |
| 491 | Rejeição: IE autorizador divergente | Verificar |
| 492 | Rejeição: IE emitente divergente | Verificar |
| 493 | Rejeição: IE destinatário divergente | Verificar |
| 494 | Rejeição: IE autorizador divergente | Verificar |
| 495 | Rejeição: IE emitente divergente | Verificar |
| 496 | Rejeição: IE destinatário divergente | Verificar |
| 497 | Rejeição: IE autorizador divergente | Verificar |
| 498 | Rejeição: IE emitente divergente | Verificar |
| 499 | Rejeição: IE destinatário divergente | Verificar |

## Referências
- Portal Nacional da NF-e: https://www.nfe.fazenda.gov.br/portal/
- Leiaute da NF-e: https://www.portalfiscal.inf.br/nfe/
- Leiaute dos Eventos: https://www.portalfiscal.inf.br/nfe/
