# All puzzles on chain

1,373 puzzle keys, 171,716,071 spends, heights 0 to 9,472,275.

A puzzle key is the list of layer mod hashes of a puzzle, joined with `|`: two coins with the same layers have the same key.

`?abcd1234` = layer not in any catalog (first 8 hex of its mod hash). In families, `*` = a layer seen in only one puzzle key (per-instance data read as a layer), and `keys` = how many puzzle keys are in the family.

- 1 layer, unknown: 124
- 1 layer, known: 32
- 2+ layers, unknown: 1,103
- 2+ layers, known: 109
- not curried, unknown: 4
- quoted, known: 1

## Families with 2+ layers (184)

| spends | first | last | keys | known names | layers |
|---:|---:|---:|---:|---|---|
| 7,336,067 | 2,312,484 | 9,472,265 | 1 | CAT_V2 - standard transaction | --cni-cat_puzzles-cat_v2 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 3,751,714 | 2,178,077 | 9,472,227 | 1 | NFT_V1 - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2,892,846 | 500,057 | 9,472,275 | 1 | PLOTNFT - pool member | --cni-singleton_top_layer / --cni-pool_puzzles-pool_member_innerpuz |
| 1,962,753 | 493,764 | 9,472,275 | 1 | PLOTNFT - waiting room | --cni-singleton_top_layer / --cni-pool_puzzles-pool_waitingroom_innerpuz |
| 1,205,853 | 3,222,436 | 9,472,265 | 1 | CAT_V2 - settlement payments | --cni-cat_puzzles-cat_v2 / --cni-settlement_payments |
| 1,063,249 | 1,146,892 | 5,431,777 | 1 | CAT_V1 - standard transaction | --chia_blockchain_cat_v1-cat / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 798,885 | 2,174,322 | 9,472,227 | 1 | DID_V1 - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-did_puzzles-did_innerpuz / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 391,279 | 3,180,127 | 9,472,010 | 1 | NFT_V1 - settlement payments | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-settlement_payments |
| 329,144 | 3,663,706 | 9,195,584 | 1 | TIBET_SWAP - liquidity pair v1 | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet-pair_inner_puzzle |
| 328,748 | 3,663,922 | 9,195,584 | 1 | TIBET_SWAP - CAT reserve (p2 singleton flashloan) | --cni-cat_puzzles-cat_v2 / --tibet-p2_singleton_flashloan |
| 315,421 | 6,632,156 | 8,845,800 | 11 |  | --cni-singleton_top_layer_v1_1 / * |
| 258,336 | 7,527,616 | 9,471,698 | 13 |  | * / ?2d55c090 / ?58006121 |
| 186,916 | 8,135,445 | 9,472,275 | 1 | CIRCUIT - atom announcer | unknown_puzz_02 / --circuit-circuit_puzzles-atom_announcer |
| 129,141 | 710,169 | 9,471,006 | 131 |  | * / * |
| 128,156 | 3,255,497 | 9,472,275 | 8 |  | --cni-cat_puzzles-cat_v2 / * / * |
| 114,631 | 2,312,817 | 8,684,688 | 1 |  | --cni-cat_puzzles-cat_v2 / ?9a6c5ff6 |
| 107,755 | 2,812,757 | 9,464,022 | 1 |  | ?1b08dc6c / ?f992d595 |
| 99,263 | 3,237,645 | 9,471,006 | 12 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / * / * |
| 81,141 | 2,178,297 | 7,841,416 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?9a6c5ff6 |
| 55,783 | 2,174,316 | 9,471,467 | 1 | NFT_V1 - no ownership layer, standard transaction | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 47,010 | 6,758,689 | 9,471,923 | 1 | VAULT - pay to vault (singleton member) | --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 30,336 | 1,243,725 | 3,050,466 | 1 |  | --chia_blockchain_cat_v1-cat / ?9a6c5ff6 |
| 28,645 | 6,758,689 | 9,472,054 | 1 | VAULT - vault singleton, 1 of n | --cni-singleton_top_layer_v1_1 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 28,323 | 6,806,445 | 9,464,823 | 1 | CAT_V2 - pay to vault (singleton member) | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 24,345 | 7,527,616 | 9,471,698 | 1 |  | --cni-cat_puzzles-cat_v2 / ?25fbd0d4 / ?87a17c3e |
| 24,345 | 7,527,616 | 9,471,698 | 6 |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / * / ?d277207e / ?745f24f6 |
| 21,282 | 7,975,726 | 8,135,373 | 2 |  | * / * / ?00d20b97 |
| 13,789 | 8,039,436 | 9,472,191 | 5 | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / * / --circuit-circuit_puzzles-statutes |
| 13,560 | 2,751,545 | 9,472,205 | 18 |  | --cni-singleton_top_layer_v1_1 / * / * |
| 11,347 | 9,036,761 | 9,472,275 | 17 | SLOT_MACHINE - slot | * / --slot_machine_rue-singleton-slot |
| 10,884 | 7,284,177 | 9,467,812 | 8 |  | --cni-singleton_top_layer_v1_1 / * / ?2576e15e |
| 8,449 | 2,812,757 | 9,428,936 | 1 |  | --cni-cat_puzzles-cat_v2 / ?1b08dc6c / ?f992d595 |
| 7,815 | 5,392,107 | 9,471,668 | 3 | WARP_GREEN - portal receiver | --cni-singleton_top_layer_v1_1 / * / --warp-portal_receiver |
| 7,679 | 5,392,107 | 9,471,668 | 1 | WARP_GREEN - message coin | * / --warp-message_coin |
| 7,306 | 7,284,177 | 9,467,812 | 2 |  | * / ?f38ae27c |
| 6,896 | 5,393,954 | 9,471,668 | 1 |  | --cni-cat_puzzles-cat_v2 / --warp-wrapped_cats-p2_controller_puzzle_hash |
| 6,782 | 8,135,316 | 9,462,000 | 1 | CIRCUIT - collateral vault | * / --circuit-circuit_puzzles-collateral_vault |
| 6,402 | 8,135,314 | 9,472,191 | 1 | CIRCUIT - oracle | --cni-singleton_top_layer_v1_1 / * / --circuit-circuit_puzzles-oracle |
| 6,188 | 7,534,069 | 9,398,616 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / ?25fbd0d4 / ?87a17c3e |
| 5,737 | 7,248,075 | 9,472,054 | 1 | CAT_V2 - revocable (revocation layer) | --cni-cat_puzzles-cat_v2 / --cni-vc_puzzles-revocation_layer |
| 4,431 | 8,168,935 | 8,515,280 | 502 |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / * / ?34b1f957 / ?c5d05613 |
| 4,178 | 7,973,281 | 9,461,182 | 1 | CIRCUIT - run CAT tail | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-run_tail |
| 3,863 | 9,174,976 | 9,401,356 | 1 | XCHANDLES - registration precommit (CAT) | --cni-cat_puzzles-cat_v2 / * / --slot_machine_rue-singleton-precommit |
| 3,550 | 4,272,962 | 8,844,617 | 1 | CAT_V2 - delegated conditions | --cni-cat_puzzles-cat_v2 / --cni-p2_delegated_conditions |
| 3,459 | 2,771,831 | 8,917,675 | 1 |  | ?c01ab057 / ?f992d595 |
| 3,204 | 4,978,804 | 8,609,815 | 1 |  | ?00323215 / ?a3c21438 |
| 2,369 | 4,987,064 | 8,647,306 | 1 |  | --cni-cat_puzzles-cat_v2 / ?00323215 / ?a3c21438 |
| 1,938 | 3,651,612 | 9,471,621 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties |
| 1,869 | 9,036,761 | 9,472,275 | 1 |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 1,851 | 8,135,372 | 9,466,980 | 1 |  | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-treasury |
| 1,620 | 5,392,107 | 9,468,854 | 1 | WARP_GREEN - mint and payout (CAT_V2) | --cni-cat_puzzles-cat_v2 / --warp-wrapped_assets-cat_mint_and_payout |
| 1,562 | 9,236,083 | 9,461,427 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 1,555 | 5,392,149 | 9,467,195 | 12 | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --warp-wrapped_assets-burn_inner_puzzle |
| 1,450 | 6,187,788 | 8,609,815 | 1 |  | ?f36f91db / ?be055d94 |
| 1,293 | 5,799,968 | 9,467,635 | 1 | DIG - datalayer store (delegation layer) | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --dig_datalayer-delegation_layer |
| 1,116 | 6,187,326 | 8,624,236 | 1 |  | --cni-cat_puzzles-cat_v2 / ?f36f91db / ?be055d94 |
| 961 | 9,036,761 | 9,472,275 | 5 |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / * / --slot_machine_rue-singleton-reserve_finalizer |
| 822 | 8,135,830 | 9,466,980 | 1 | CIRCUIT - savings vault (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-savings_vault / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 714 | 2,806,252 | 9,048,750 | 1 |  | --cni-cat_puzzles-cat_v2 / ?c01ab057 / ?f992d595 |
| 675 | 7,701,523 | 9,195,775 | 1 | TIBET_SWAP - liquidity pair v2 | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet-v2r_pair_inner_puzzle |
| 621 | 7,491,664 | 9,471,923 | 1 | OPTION_CONTRACT - standard transaction | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 584 | 3,563,941 | 3,603,036 | 1 | TIBET_SWAP - liquidity pair v1 beta (before the April 2023 fix) | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet_v1_beta-pair_inner_puzzle |
| 563 | 3,563,949 | 3,603,036 | 1 | TIBET_SWAP - CAT reserve v1 beta | --cni-cat_puzzles-cat_v2 / --tibet_v1_beta-p2_singleton_flashloan |
| 563 | 4,381,840 | 4,531,646 | 2 |  | --cni-singleton_top_layer_v1_1 / * / ?679d2a21 |
| 536 | 9,413,404 | 9,471,729 | 21 | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / * / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 522 | 8,187,132 | 8,278,771 | 2 |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / * / ?f2c96e97 / ?aedd3124 |
| 507 | 4,385,233 | 4,512,185 | 1 |  | ?25169a34 / ?c9d2983e |
| 458 | 1,626,563 | 2,777,394 | 2 |  | * / * / * / * |
| 443 | 4,384,982 | 4,512,185 | 1 |  | --cni-cat_puzzles-cat_v2 / ?25169a34 / ?c9d2983e |
| 393 | 8,681,195 | 9,459,307 | 53 |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / * / --slot_machine_rue-singleton-finalizer |
| 391 | 7,959,302 | 8,135,368 | 2 |  | --cni-singleton_top_layer_v1_1 / * / * / ?6bf61e08 |
| 374 | 3,663,683 | 9,089,593 | 1 | TIBET_SWAP - router v1 | --cni-singleton_top_layer_v1_1 / --tibet-router |
| 361 | 7,305,142 | 9,412,263 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 310 | 4,278,687 | 8,717,236 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_delegated_conditions |
| 256 | 7,075,506 | 9,453,608 | 41 |  | --cni-cat_puzzles-cat_v2 / * / --streaming-stream |
| 246 | 564,205 | 1,128,699 | 1 |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 240 | 4,071,049 | 4,376,172 | 1 |  | ?2a14be2a / ?5e96a6f0 |
| 239 | 9,225,254 | 9,325,897 | 1 | REWARD_DIST - CAT pay to parent (Rue) | --cni-cat_puzzles-cat_v2 / --reward_distributor-p2_parent_v2 / --slot_machine_rue-default_puzzles-default_cat_maker |
| 236 | 7,959,302 | 8,034,991 | 3 |  | --circuit-circuit_puzzles-singleton_top_layer_isa / * / ?7c62fa84 / ?91a93448 |
| 234 | 9,010,907 | 9,195,572 | 1 | CIRCUIT - surplus auction (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-surplus_auction |
| 227 | 4,070,294 | 4,375,657 | 1 |  | --cni-cat_puzzles-cat_v2 / ?2a14be2a / ?5e96a6f0 |
| 225 | 2,600,663 | 8,839,783 | 6 |  | --cni-cat_puzzles-cat_v2 / * |
| 192 | 2,751,667 | 9,463,246 | 15 |  | * / ?fa279361 / ?17bc4080 |
| 174 | 8,161,876 | 9,155,456 | 1 | SINGLETON - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 158 | 7,832,091 | 9,386,342 | 1 |  | --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 155 | 3,859,092 | 5,950,592 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-vc_puzzles-exigent_metadata_layer / --cni-vc_puzzles-p2_announced_delegated_puzzle |
| 155 | 3,868,630 | 6,451,776 | 1 | VC - verified credential | --cni-singleton_top_layer_v1_1 / --cni-vc_puzzles-exigent_metadata_layer / --cni-vc_puzzles-eml_transfer_program_covenant_adapter / --cni-vc_puzzles-covenant_layer / * / --cni-vc_puzzles-eml_covenant_morpher / --cni-vc_puzzles-eml_update_metadata_with_DID / --cni-vc_puzzles-revocation_layer |
| 130 | 7,407,976 | 9,370,170 | 1 |  | --cni-cat_puzzles-cat_v2 / --cni-p2_1_of_n |
| 106 | 8,071,062 | 9,265,031 | 1 |  | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 105 | 2,422,928 | 8,943,153 | 1 |  | ?8390fc59 / ?2d0aeb4c |
| 105 | 2,171,630 | 2,484,806 | 2 |  | * / ?cdf47b5c |
| 94 | 8,657,271 | 8,663,316 | 39 |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / * / ?9121874f |
| 78 | 4,322,996 | 4,423,200 | 2 |  | * / ?f151a226 |
| 74 | 916,428 | 1,128,450 | 1 |  | ?e9bf0503 / ?b11155ab |
| 68 | 8,658,318 | 8,663,077 | 58 |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / * / ?5b4289f5 |
| 61 | 4,291,275 | 4,662,284 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?0b1a2cfa / ?e4ca85aa |
| 61 | 8,135,362 | 9,182,184 | 1 | CIRCUIT - governance (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-governance |
| 60 | 3,135,017 | 3,420,768 | 1 |  | --cni-singleton_top_layer_v1_1 / * / * / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 54 | 8,681,391 | 8,691,360 | 31 |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / * / ?63fff50f |
| 53 | 916,428 | 1,128,450 | 1 |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?4485b963 / ?37e340b9 |
| 43 | 8,154,107 | 8,347,303 | 3 |  | --cni-cat_puzzles-cat_v2 / * / ?4ba89147 |
| 40 | 916,703 | 1,127,633 | 1 |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?e9bf0503 / ?b11155ab |
| 39 | 7,491,674 | 9,061,268 | 1 | OPTION_CONTRACT - settlement payments | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-settlement_payments |
| 36 | 856,020 | 4,408,604 | 2 |  | * / ?ee28acae |
| 36 | 7,973,288 | 8,040,447 | 2 |  | --cni-cat_puzzles-cat_v2 / * / * / ?693e0175 |
| 34 | 440,528 | 556,663 | 2 |  | ?bb1c4e9f / ?56b0177e / * / * |
| 31 | 2,423,352 | 5,438,780 | 1 |  | --cni-cat_puzzles-cat_v2 / ?8390fc59 / ?2d0aeb4c |
| 31 | 832,085 | 2,249,672 | 3 |  | --cni-singleton_top_layer / * / * |
| 30 | 9,412,345 | 9,445,847 | 1 | FORGE - CAT reserve launcher | --cni-cat_puzzles-cat_v2 / --forge_v16-forge_reserve_launcher |
| 28 | 8,819,269 | 9,088,648 | 4 |  | --cni-singleton_top_layer_v1_1 / * / ?e572d641 |
| 26 | 9,010,907 | 9,195,572 | 1 | CIRCUIT - payout (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-payout |
| 24 | 2,073,001 | 4,760,153 | 1 |  | ?f1e8350c / ?7302d5c2 / --cni-did_puzzles-did_innerpuz / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 24 | 5,790,274 | 5,792,237 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / * / * |
| 22 | 916,703 | 1,127,633 | 1 |  | ?4485b963 / ?37e340b9 |
| 21 | 9,310,509 | 9,379,313 | 2 |  | --cni-cat_puzzles-cat_v2 / * / ?d744b1ce |
| 18 | 9,037,793 | 9,047,215 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 18 | 8,039,436 | 8,259,827 | 2 | CIRCUIT - announcer registry | * / --circuit-circuit_puzzles-announcer_registry |
| 17 | 3,560,549 | 3,575,110 | 1 | TIBET_SWAP - router v1 beta | --cni-singleton_top_layer_v1_1 / --tibet_v1_beta-router |
| 17 | 7,673,847 | 7,870,042 | 1 | SINGLETON - multisig (m of n keys) | --cni-singleton_top_layer_v1_1 / --cni-p2_m_of_n_delegate_direct |
| 17 | 1,368,910 | 2,015,283 | 2 |  | * / ?430d155b |
| 15 | 9,176,142 | 9,239,439 | 1 | SLOT_MACHINE - state scheduler | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-state_scheduler |
| 15 | 7,959,327 | 8,039,817 | 2 |  | * / * / ?4ba93c16 |
| 12 | 8,039,436 | 9,010,795 | 1 | CIRCUIT - governance launcher (CAT_V2) | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-governance_launcher |
| 11 | 3,427,617 | 7,154,178 | 1 | NFT_V1 - no ownership layer, settlement payments | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-settlement_payments |
| 10 | 834,768 | 852,866 | 2 |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / * / * |
| 10 | 1,898,893 | 2,311,203 | 2 |  | --chia_blockchain_cat_v1-cat / * |
| 9 | 7,977,700 | 9,007,408 | 1 |  | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-governance_exit |
| 9 | 8,818,187 | 8,829,672 | 2 |  | --cni-singleton_top_layer_v1_1 / * / ?74a2efca |
| 8 | 1,165,352 | 1,373,636 | 1 |  | ?2859f5d6 / ?5c554c87 |
| 7 | 7,701,523 | 7,838,927 | 1 | TIBET_SWAP - router v2 | --cni-singleton_top_layer_v1_1 / --tibet-v2r_router |
| 7 | 8,230,897 | 8,975,964 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 7 | 9,047,770 | 9,061,243 | 1 |  | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract |
| 7 | 7,959,302 | 7,976,207 | 2 |  | * / ?5f5eb85d / ?d16bbd9e |
| 6 | 1,165,352 | 1,371,224 | 1 |  | --chia_blockchain_cat_v1-cat / ?6dcdbf2a / ?4bc34f7c |
| 6 | 2,123,088 | 2,243,839 | 1 |  | ?f1e8350c / ?7302d5c2 / ?31f5e810 / ?3dad4a24 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 6 | 9,047,988 | 9,061,273 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_1_of_n |
| 6 | 9,051,135 | 9,051,170 | 1 | REWARD_DIST - CAT pay to next epoch | --cni-cat_puzzles-cat_v2 / --reward_distributor_rue-p2_next_reward_distributor_epoch |
| 6 | 1,991,167 | 2,120,587 | 2 |  | ?f1e8350c / ?7302d5c2 / * / ?610ef9a4 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 6 | 5,613,011 | 5,613,415 | 2 |  | --cni-singleton_top_layer_v1_1 / * / * / * |
| 6 | 7,973,296 | 8,039,825 | 2 |  | --cni-cat_puzzles-cat_v2 / * / * / * |
| 5 | 1,154,467 | 1,371,114 | 1 |  | --chia_blockchain_cat_v1-cat / ?2859f5d6 / ?5c554c87 |
| 5 | 1,154,467 | 1,371,114 | 1 |  | ?6dcdbf2a / ?4bc34f7c |
| 5 | 2,244,754 | 2,376,184 | 1 |  | ?7ce9095a / ?6dcc5a7c |
| 5 | 6,450,243 | 6,450,602 | 1 |  | --cni-cat_puzzles-cat_v2 / ?85cd51da / ?6fb00617 / ?6db22474 / ?e409fced |
| 4 | 1,210,005 | 1,568,383 | 1 |  | --chia_blockchain_cat_v1-cat / --chia_blockchain_cat_v1-cat / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 4 | 9,046,103 | 9,051,071 | 1 |  | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 4 | 9,391,763 | 9,423,322 | 1 | VAULT - vault singleton, m of n | --cni-singleton_top_layer_v1_1 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-m_of_n |
| 4 | 9,033,805 | 9,091,954 | 2 |  | * / ?449001e0 |
| 3 | 1,604,018 | 1,661,191 | 1 |  | --chia_blockchain_cat_v1-cat / ?a897c8f1 / ?aaa20810 |
| 3 | 2,264,392 | 4,186,277 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / ?9a6c5ff6 |
| 3 | 2,373,971 | 2,374,562 | 1 |  | --cni-cat_puzzles-cat_v2 / ?7ce9095a / ?6dcc5a7c |
| 3 | 3,043,223 | 3,050,994 | 1 |  | ?b6e32301 / ?80f50d4b |
| 3 | 5,613,011 | 5,613,415 | 1 |  | * / * / * |
| 3 | 7,823,074 | 7,823,573 | 1 | REWARD_DIST - CAT pay to parent (Chialisp) | --cni-cat_puzzles-cat_v2 / --reward_distributor-p2_parent_v2 / --slot_machine-default_puzzles-default_cat_maker |
| 3 | 812,237 | 813,229 | 2 |  | * / ?669252a6 |
| 2 | 1,211,109 | 1,211,123 | 1 |  | ?bb9ed2fd / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2 | 1,211,545 | 1,211,550 | 1 |  | ?fe8f5c74 / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2 | 2,382,288 | 2,382,925 | 1 |  | ?238e8e3c / ?a3107477 |
| 2 | 2,382,925 | 2,382,956 | 1 |  | --cni-cat_puzzles-cat_v2 / ?238e8e3c / ?a3107477 |
| 2 | 3,236,659 | 3,236,659 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?b6e32301 / ?80f50d4b |
| 2 | 3,521,593 | 3,535,199 | 1 |  | --cni-singleton_top_layer_v1_1 / ?849d8852 / ?82d8ceb1 / --cni-vc_puzzles-eml_transfer_program_covenant_adapter / --cni-vc_puzzles-covenant_layer / * / --cni-vc_puzzles-eml_covenant_morpher / * / * / --cni-vc_puzzles-revocation_layer |
| 2 | 4,304,958 | 4,305,225 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / ?0b1a2cfa / ?e4ca85aa |
| 2 | 6,441,193 | 6,441,242 | 1 |  | ?85cd51da / ?6fb00617 / ?6db22474 / ?e409fced |
| 2 | 1,889,234 | 1,889,297 | 2 |  | * / ?8127e18e |
| 2 | 7,973,313 | 8,039,840 | 2 |  | --cni-cat_puzzles-cat_v2 / * / * / ?5b9b86da |
| 1 | 1,210,938 | 1,210,938 | 1 |  | * / ?ba7dbcc0 |
| 1 | 1,211,092 | 1,211,092 | 1 |  | ?bb9ed2fd / ?ba7dbcc0 |
| 1 | 1,211,142 | 1,211,142 | 1 |  | ?bb9ed2fd / ?ba7dbcc0 / ?bb9ed2fd / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 1,211,535 | 1,211,535 | 1 |  | ?fe8f5c74 / ?ba7dbcc0 |
| 1 | 1,213,331 | 1,213,331 | 1 |  | ?fe8f5c74 / ?ba7dbcc0 / ?fe8f5c74 / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 1,421,131 | 1,421,131 | 1 | CAT_V1 - delegated conditions | --chia_blockchain_cat_v1-cat / --cni-p2_delegated_conditions |
| 1 | 1,594,642 | 1,594,642 | 1 |  | ?a897c8f1 / ?aaa20810 |
| 1 | 1,859,346 | 1,859,346 | 1 |  | --chia_blockchain_cat_v1-cat / * / * |
| 1 | 2,243,908 | 2,243,908 | 1 |  | ?f1e8350c / ?7302d5c2 / ?31f5e810 / ?3dad4a24 / * / * / * / * / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 3,051,007 | 3,051,007 | 1 |  | --cni-cat_puzzles-cat_v2 / ?b6e32301 / ?80f50d4b |
| 1 | 3,288,047 | 3,288,047 | 1 |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?8390fc59 / ?2d0aeb4c |
| 1 | 3,511,766 | 3,511,766 | 1 |  | --cni-singleton_top_layer_v1_1 / ?849d8852 / ?82d8ceb1 / --cni-vc_puzzles-p2_announced_delegated_puzzle |
| 1 | 3,647,889 | 3,647,889 | 1 |  | --cni-singleton_top_layer_v1_1 / * / * / * / * |
| 1 | 5,073,066 | 5,073,066 | 1 |  | --cni-cat_puzzles-cat_v2 / ?79bd0d65 / ?32c10874 |
| 1 | 5,076,522 | 5,076,522 | 1 |  | --cni-cat_puzzles-cat_v2 / ?79bd0d65 / ?32c10874 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 7,502,235 | 7,502,235 | 1 |  | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-p2_1_of_n |
| 1 | 7,710,612 | 7,710,612 | 1 |  | ?25fbd0d4 / ?87a17c3e |
| 1 | 8,135,381 | 8,135,381 | 1 | CIRCUIT - recharge auction (CAT_V2) | --cni-cat_puzzles-cat_v2 / * / --circuit-circuit_puzzles-recharge_auction |
| 1 | 8,665,044 | 8,665,044 | 1 |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / * / * |

## All with 2+ layers

| spends | first | last | known | name | layers |
|---:|---:|---:|---|---|---|
| 7,336,067 | 2,312,484 | 9,472,265 | yes | CAT_V2 - standard transaction | --cni-cat_puzzles-cat_v2 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 3,751,714 | 2,178,077 | 9,472,227 | yes | NFT_V1 - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2,892,846 | 500,057 | 9,472,275 | yes | PLOTNFT - pool member | --cni-singleton_top_layer / --cni-pool_puzzles-pool_member_innerpuz |
| 1,962,753 | 493,764 | 9,472,275 | yes | PLOTNFT - waiting room | --cni-singleton_top_layer / --cni-pool_puzzles-pool_waitingroom_innerpuz |
| 1,205,853 | 3,222,436 | 9,472,265 | yes | CAT_V2 - settlement payments | --cni-cat_puzzles-cat_v2 / --cni-settlement_payments |
| 1,063,249 | 1,146,892 | 5,431,777 | yes | CAT_V1 - standard transaction | --chia_blockchain_cat_v1-cat / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 798,885 | 2,174,322 | 9,472,227 | yes | DID_V1 - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-did_puzzles-did_innerpuz / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 391,279 | 3,180,127 | 9,472,010 | yes | NFT_V1 - settlement payments | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-settlement_payments |
| 329,144 | 3,663,706 | 9,195,584 | yes | TIBET_SWAP - liquidity pair v1 | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet-pair_inner_puzzle |
| 328,748 | 3,663,922 | 9,195,584 | yes | TIBET_SWAP - CAT reserve (p2 singleton flashloan) | --cni-cat_puzzles-cat_v2 / --tibet-p2_singleton_flashloan |
| 315,288 | 6,632,156 | 6,636,200 |  |  | --cni-singleton_top_layer_v1_1 / ?94bb8d5d |
| 241,458 | 7,537,628 | 9,398,616 |  |  | ?5d968e2b / ?2d55c090 / ?58006121 |
| 186,916 | 8,135,445 | 9,472,275 | yes | CIRCUIT - atom announcer | unknown_puzz_02 / --circuit-circuit_puzzles-atom_announcer |
| 125,910 | 8,521,893 | 9,472,275 |  |  | --cni-cat_puzzles-cat_v2 / ?6bf273ca / ?6a686612 |
| 114,631 | 2,312,817 | 8,684,688 |  |  | --cni-cat_puzzles-cat_v2 / ?9a6c5ff6 |
| 107,755 | 2,812,757 | 9,464,022 |  |  | ?1b08dc6c / ?f992d595 |
| 81,141 | 2,178,297 | 7,841,416 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?9a6c5ff6 |
| 59,194 | 6,278,514 | 9,085,265 |  |  | ?e5c40e23 / ?a68bf288 |
| 55,783 | 2,174,316 | 9,471,467 | yes | NFT_V1 - no ownership layer, standard transaction | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 52,792 | 6,419,677 | 9,471,006 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?30b4e407 / ?0964de17 |
| 47,010 | 6,758,689 | 9,471,923 | yes | VAULT - pay to vault (singleton member) | --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 38,894 | 5,031,352 | 9,471,006 |  |  | ?0fcdee23 / ?63e7d759 |
| 30,336 | 1,243,725 | 3,050,466 |  |  | --chia_blockchain_cat_v1-cat / ?9a6c5ff6 |
| 28,645 | 6,758,689 | 9,472,054 | yes | VAULT - vault singleton, 1 of n | --cni-singleton_top_layer_v1_1 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 28,323 | 6,806,445 | 9,464,823 | yes | CAT_V2 - pay to vault (singleton member) | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 24,761 | 6,269,607 | 9,069,444 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?d76d5a8d / ?ad877ec0 |
| 24,345 | 7,527,616 | 9,471,698 |  |  | --cni-cat_puzzles-cat_v2 / ?25fbd0d4 / ?87a17c3e |
| 17,129 | 8,959,540 | 9,471,698 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?74c706d8 / ?d277207e / ?745f24f6 |
| 16,633 | 8,962,412 | 9,471,698 |  |  | ?51b72a06 / ?2d55c090 / ?58006121 |
| 13,554 | 8,135,347 | 9,472,191 | yes | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / ?2f977164 / --circuit-circuit_puzzles-statutes |
| 12,910 | 8,040,234 | 8,135,373 |  |  | ?1ac338c3 / ?df3d4889 / ?00d20b97 |
| 12,648 | 7,863,865 | 9,449,057 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?4042eb1c / ?9fd85613 |
| 12,599 | 4,061,695 | 4,376,896 |  |  | --cni-singleton_top_layer_v1_1 / ?635fe962 / ?9ef9374a |
| 11,341 | 2,184,609 | 7,793,019 |  |  | ?1b51792b / ?481089e1 |
| 9,376 | 7,284,177 | 9,467,812 |  |  | ?7a45acf0 / ?2322aad5 |
| 8,449 | 2,812,757 | 9,428,936 |  |  | --cni-cat_puzzles-cat_v2 / ?1b08dc6c / ?f992d595 |
| 8,372 | 7,975,726 | 8,035,081 |  |  | ?8f72dab9 / ?6434b77c / ?00d20b97 |
| 7,787 | 9,174,976 | 9,459,307 | yes | SLOT_MACHINE - slot | ?c6d65bf4 / --slot_machine_rue-singleton-slot |
| 7,679 | 5,392,107 | 9,471,668 | yes | WARP_GREEN - message coin | ?8759e725 / --warp-message_coin |
| 7,380 | 5,394,203 | 8,940,588 | yes | WARP_GREEN - portal receiver | --cni-singleton_top_layer_v1_1 / ?42962075 / --warp-portal_receiver |
| 7,148 | 7,537,587 | 9,398,616 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a9ea390d / ?d277207e / ?745f24f6 |
| 6,896 | 5,393,954 | 9,471,668 |  |  | --cni-cat_puzzles-cat_v2 / --warp-wrapped_cats-p2_controller_puzzle_hash |
| 6,782 | 8,135,316 | 9,462,000 | yes | CIRCUIT - collateral vault | ?c092cc68 / --circuit-circuit_puzzles-collateral_vault |
| 6,402 | 8,135,314 | 9,472,191 | yes | CIRCUIT - oracle | --cni-singleton_top_layer_v1_1 / ?936bf057 / --circuit-circuit_puzzles-oracle |
| 6,318 | 7,521,904 | 8,880,975 |  |  | --cni-singleton_top_layer_v1_1 / ?fd2b411a / ?2576e15e |
| 6,297 | 5,031,352 | 9,305,099 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?79955b44 / ?1d48de8f |
| 6,188 | 7,534,069 | 9,398,616 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / ?25fbd0d4 / ?87a17c3e |
| 6,059 | 7,284,177 | 8,972,101 |  |  | ?c35894dc / ?f38ae27c |
| 5,737 | 7,248,075 | 9,472,054 | yes | CAT_V2 - revocable (revocation layer) | --cni-cat_puzzles-cat_v2 / --cni-vc_puzzles-revocation_layer |
| 4,178 | 7,973,281 | 9,461,182 | yes | CIRCUIT - run CAT tail | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-run_tail |
| 3,863 | 9,174,976 | 9,401,356 | yes | XCHANDLES - registration precommit (CAT) | --cni-cat_puzzles-cat_v2 / ?ac3ce007 / --slot_machine_rue-singleton-precommit |
| 3,550 | 4,272,962 | 8,844,617 | yes | CAT_V2 - delegated conditions | --cni-cat_puzzles-cat_v2 / --cni-p2_delegated_conditions |
| 3,459 | 2,771,831 | 8,917,675 |  |  | ?c01ab057 / ?f992d595 |
| 3,204 | 4,978,804 | 8,609,815 |  |  | ?00323215 / ?a3c21438 |
| 3,024 | 1,836,464 | 2,189,768 |  |  | ?8fc6fdba / ?899a1fd1 |
| 3,021 | 2,012,597 | 2,189,768 |  |  | ?61e7579e / ?fa97608e |
| 2,411 | 8,179,800 | 8,278,732 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?88425a14 / ?34b1f957 / ?c5d05613 |
| 2,369 | 4,987,064 | 8,647,306 |  |  | --cni-cat_puzzles-cat_v2 / ?00323215 / ?a3c21438 |
| 2,070 | 6,136,681 | 9,277,079 |  |  | --cni-cat_puzzles-cat_v2 / ?32a03a8b / ?11b78a8a |
| 1,938 | 3,651,612 | 9,471,621 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties |
| 1,869 | 9,036,761 | 9,472,275 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 1,851 | 8,135,372 | 9,466,980 |  |  | --cni-cat_puzzles-cat_v2 / ?c2638d28 / --circuit-circuit_puzzles-treasury |
| 1,763 | 9,066,204 | 9,467,812 |  |  | --cni-singleton_top_layer_v1_1 / ?86361d36 / ?2576e15e |
| 1,620 | 5,392,107 | 9,468,854 | yes | WARP_GREEN - mint and payout (CAT_V2) | --cni-cat_puzzles-cat_v2 / --warp-wrapped_assets-cat_mint_and_payout |
| 1,596 | 5,776,209 | 9,452,251 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?9f6f4a9b / ?6b41e2f6 |
| 1,562 | 9,236,083 | 9,461,427 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 1,541 | 9,310,067 | 9,426,145 | yes | SLOT_MACHINE - slot | ?6ca6c2d8 / --slot_machine_rue-singleton-slot |
| 1,450 | 6,187,788 | 8,609,815 |  |  | ?f36f91db / ?be055d94 |
| 1,390 | 9,309,956 | 9,471,935 | yes | SLOT_MACHINE - slot | ?c4cc8047 / --slot_machine_rue-singleton-slot |
| 1,312 | 7,284,177 | 7,526,294 |  |  | --cni-singleton_top_layer_v1_1 / ?c0eabcd1 / ?2576e15e |
| 1,293 | 5,799,968 | 9,467,635 | yes | DIG - datalayer store (delegation layer) | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --dig_datalayer-delegation_layer |
| 1,247 | 8,970,053 | 9,467,812 |  |  | ?0ae81478 / ?f38ae27c |
| 1,142 | 5,393,795 | 9,467,195 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?98613dc6 / --warp-wrapped_assets-burn_inner_puzzle |
| 1,116 | 6,187,326 | 8,624,236 |  |  | --cni-cat_puzzles-cat_v2 / ?f36f91db / ?be055d94 |
| 1,002 | 6,980,642 | 7,562,232 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?66a82ae5 / ?715e760e |
| 822 | 8,135,830 | 9,466,980 | yes | CIRCUIT - savings vault (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?2a3922ea / --circuit-circuit_puzzles-savings_vault / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 794 | 8,832,316 | 8,972,101 |  |  | --cni-singleton_top_layer_v1_1 / ?e7c9e5b6 / ?2576e15e |
| 714 | 2,806,252 | 9,048,750 |  |  | --cni-cat_puzzles-cat_v2 / ?c01ab057 / ?f992d595 |
| 675 | 7,701,523 | 9,195,775 | yes | TIBET_SWAP - liquidity pair v2 | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet-v2r_pair_inner_puzzle |
| 621 | 7,491,664 | 9,471,923 | yes | OPTION_CONTRACT - standard transaction | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 584 | 3,563,941 | 3,603,036 | yes | TIBET_SWAP - liquidity pair v1 beta (before the April 2023 fix) | --cni-singleton_top_layer_v1_1 / --tibet-p2_merkle_tree_modified / --tibet_v1_beta-pair_inner_puzzle |
| 563 | 3,563,949 | 3,603,036 | yes | TIBET_SWAP - CAT reserve v1 beta | --cni-cat_puzzles-cat_v2 / --tibet_v1_beta-p2_singleton_flashloan |
| 543 | 8,844,514 | 9,027,849 |  |  | --cni-singleton_top_layer_v1_1 / ?e95fb6ab / ?b4023b35 |
| 515 | 4,416,979 | 4,531,646 |  |  | --cni-singleton_top_layer_v1_1 / ?5a1b4066 / ?679d2a21 |
| 507 | 4,385,233 | 4,512,185 |  |  | ?25169a34 / ?c9d2983e |
| 459 | 9,309,854 | 9,471,935 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e62f1b22 / --slot_machine_rue-singleton-reserve_finalizer |
| 457 | 1,626,563 | 2,519,208 |  |  | ?ffc0846e / ?803113b3 / ?dff4698a / ?f09a43c3 |
| 454 | 5,446,683 | 8,320,946 |  |  | ?ad760f8c / ?95efa041 |
| 443 | 4,384,982 | 4,512,185 |  |  | --cni-cat_puzzles-cat_v2 / ?25169a34 / ?c9d2983e |
| 443 | 5,447,264 | 8,320,946 |  |  | ?4b3574cf / ?4ad6dfe1 |
| 429 | 8,940,709 | 9,471,668 | yes | WARP_GREEN - portal receiver | --cni-singleton_top_layer_v1_1 / ?011288ac / --warp-portal_receiver |
| 422 | 8,970,053 | 9,047,717 |  |  | --cni-singleton_top_layer_v1_1 / ?284141e9 / ?2576e15e |
| 413 | 9,236,070 | 9,472,275 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?07bad5de / --slot_machine_rue-singleton-reserve_finalizer |
| 409 | 9,236,075 | 9,472,275 | yes | SLOT_MACHINE - slot | ?0d299e54 / --slot_machine_rue-singleton-slot |
| 374 | 3,663,683 | 9,089,593 | yes | TIBET_SWAP - router v1 | --cni-singleton_top_layer_v1_1 / --tibet-router |
| 361 | 7,305,142 | 9,412,263 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-member_puzzles-singleton_member |
| 338 | 8,201,250 | 8,278,771 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?43ccb3ac / ?f2c96e97 / ?aedd3124 |
| 316 | 2,419,732 | 4,298,792 |  |  | ?86204e2c / ?8e190d0a |
| 316 | 2,419,662 | 4,291,116 |  |  | ?666a0687 / ?161c4e88 |
| 310 | 4,278,687 | 8,717,236 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_delegated_conditions |
| 301 | 5,446,683 | 8,320,916 |  |  | ?7a795544 / ?72a1b621 |
| 299 | 5,447,264 | 8,320,946 |  |  | ?6e18c2db / ?de304f9b |
| 246 | 564,205 | 1,128,699 |  |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 240 | 4,071,049 | 4,376,172 |  |  | ?2a14be2a / ?5e96a6f0 |
| 239 | 9,225,254 | 9,325,897 | yes | REWARD_DIST - CAT pay to parent (Rue) | --cni-cat_puzzles-cat_v2 / --reward_distributor-p2_parent_v2 / --slot_machine_rue-default_puzzles-default_cat_maker |
| 234 | 9,010,907 | 9,195,572 | yes | CIRCUIT - surplus auction (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?6253104c / --circuit-circuit_puzzles-surplus_auction |
| 232 | 7,973,270 | 8,034,991 |  |  | --circuit-circuit_puzzles-singleton_top_layer_isa / ?3e19df4f / ?7c62fa84 / ?91a93448 |
| 227 | 4,070,294 | 4,375,657 |  |  | --cni-cat_puzzles-cat_v2 / ?2a14be2a / ?5e96a6f0 |
| 226 | 9,174,976 | 9,459,307 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?5fcbad36 / --slot_machine_rue-singleton-finalizer |
| 223 | 8,039,808 | 8,135,368 | yes | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / ?ff3437cd / --circuit-circuit_puzzles-statutes |
| 220 | 1,087,623 | 1,232,610 |  |  | ?f950e48c / ?6ff9ada8 |
| 216 | 2,040,400 | 4,026,320 |  |  | ?27c18a9a / ?a87003ba |
| 202 | 5,392,149 | 9,337,557 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?898f6523 / --warp-wrapped_assets-burn_inner_puzzle |
| 196 | 2,751,545 | 9,472,205 |  |  | --cni-singleton_top_layer_v1_1 / ?66f0fe81 / ?0f47e70f |
| 196 | 7,959,302 | 8,034,378 |  |  | --cni-singleton_top_layer_v1_1 / ?070797f6 / ?4bd87ce0 / ?6bf61e08 |
| 195 | 8,039,436 | 8,135,368 |  |  | --cni-singleton_top_layer_v1_1 / ?c680b21c / ?b2c3bb94 / ?6bf61e08 |
| 189 | 9,043,214 | 9,084,326 |  |  | --cni-singleton_top_layer_v1_1 / ?d6f70c2f / ?2576e15e |
| 184 | 8,187,132 | 8,196,766 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e3b1513c / ?f2c96e97 / ?aedd3124 |
| 174 | 8,161,876 | 9,155,456 | yes | SINGLETON - standard transaction | --cni-singleton_top_layer_v1_1 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 158 | 7,832,091 | 9,386,342 |  |  | --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 155 | 3,859,092 | 5,950,592 |  |  | --cni-singleton_top_layer_v1_1 / --cni-vc_puzzles-exigent_metadata_layer / --cni-vc_puzzles-p2_announced_delegated_puzzle |
| 155 | 3,868,630 | 6,451,776 | yes | VC - verified credential | --cni-singleton_top_layer_v1_1 / --cni-vc_puzzles-exigent_metadata_layer / --cni-vc_puzzles-eml_transfer_program_covenant_adapter / --cni-vc_puzzles-covenant_layer / ?dd12ebf7 / --cni-vc_puzzles-eml_covenant_morpher / --cni-vc_puzzles-eml_update_metadata_with_DID / --cni-vc_puzzles-revocation_layer |
| 154 | 4,370,352 | 9,463,246 |  |  | ?2dde5c29 / ?fa279361 / ?17bc4080 |
| 150 | 2,600,663 | 7,293,003 |  |  | --cni-cat_puzzles-cat_v2 / ?7d816bf6 |
| 130 | 7,407,976 | 9,370,170 |  |  | --cni-cat_puzzles-cat_v2 / --cni-p2_1_of_n |
| 129 | 729,677 | 965,685 |  |  | ?6b578871 / ?ed16b388 |
| 123 | 8,274,700 | 8,278,771 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?07d5ffb1 / ?34b1f957 / ?c5d05613 |
| 122 | 8,417,791 | 9,343,428 |  |  | --cni-cat_puzzles-cat_v2 / ?8af5921f / ?f7c34446 |
| 119 | 5,394,267 | 9,337,557 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?0dd6e6d3 / --warp-wrapped_assets-burn_inner_puzzle |
| 118 | 8,836,492 | 9,027,849 |  |  | ?208935e8 / ?9f73a68f |
| 112 | 906,102 | 1,128,699 |  |  | ?09bf425c / ?14fda189 |
| 106 | 6,949,455 | 8,709,288 |  |  | ?93f0b47a / ?907144ea |
| 106 | 8,071,062 | 9,265,031 |  |  | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 105 | 2,422,928 | 8,943,153 |  |  | ?8390fc59 / ?2d0aeb4c |
| 102 | 2,339,518 | 2,484,806 |  |  | ?3637de09 / ?cdf47b5c |
| 102 | 2,344,240 | 2,620,817 |  |  | ?84da5711 / ?4a77f80f |
| 101 | 8,483,591 | 8,484,942 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1f94713b / ?34b1f957 / ?c5d05613 |
| 98 | 7,593,991 | 9,453,608 |  |  | --cni-cat_puzzles-cat_v2 / ?5b44238e / --streaming-stream |
| 92 | 800,986 | 912,851 |  |  | ?355aa959 / ?d7722ae6 |
| 90 | 8,274,720 | 8,278,771 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3a4c2d05 / ?34b1f957 / ?c5d05613 |
| 83 | 5,142,627 | 9,464,202 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?78ba7f11 / ?a6427461 |
| 76 | 8,819,299 | 8,828,352 |  |  | --cni-singleton_top_layer_v1_1 / ?2301e18b / ?2576e15e |
| 75 | 9,179,181 | 9,210,288 |  |  | ?f82ad35e / ?98c66c49 |
| 74 | 916,428 | 1,128,450 |  |  | ?e9bf0503 / ?b11155ab |
| 74 | 8,487,682 | 8,488,426 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3f3ef22e / ?34b1f957 / ?c5d05613 |
| 72 | 5,394,253 | 9,337,557 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?42d2731b / --warp-wrapped_assets-burn_inner_puzzle |
| 71 | 2,490,103 | 6,606,975 |  |  | ?40c3ea3e / ?0c316100 |
| 69 | 6,921,575 | 6,934,690 |  |  | ?b27f4657 / ?a7f84333 |
| 67 | 7,536,686 | 7,537,439 |  |  | ?610f1f99 / ?2d55c090 / ?58006121 |
| 67 | 8,481,678 | 8,483,320 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ab85f84b / ?34b1f957 / ?c5d05613 |
| 61 | 4,291,275 | 4,662,284 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?0b1a2cfa / ?e4ca85aa |
| 61 | 6,940,581 | 7,827,593 |  |  | ?71493847 / ?d3026ded |
| 61 | 8,135,362 | 9,182,184 | yes | CIRCUIT - governance (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?31c9645b / --circuit-circuit_puzzles-governance |
| 60 | 3,135,017 | 3,420,768 |  |  | --cni-singleton_top_layer_v1_1 / ?0f5fe8a3 / ?441c9c46 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 60 | 8,274,724 | 8,278,766 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e44ec868 / ?34b1f957 / ?c5d05613 |
| 60 | 8,479,448 | 8,485,841 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4fcb933e / ?34b1f957 / ?c5d05613 |
| 59 | 7,531,688 | 7,536,364 |  |  | ?0ff7bc06 / ?2d55c090 / ?58006121 |
| 58 | 7,533,070 | 7,536,407 |  |  | ?dcc52460 / ?2d55c090 / ?58006121 |
| 58 | 9,422,364 | 9,471,390 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f4a43e9c / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 57 | 1,957,155 | 8,027,986 |  |  | ?71a6b0dd / ?8dd4efaa |
| 57 | 8,551,225 | 9,464,202 |  |  | --cni-singleton_top_layer_v1_1 / ?1d06c31e / ?b24250fd |
| 54 | 3,222,629 | 3,905,165 |  |  | --cni-cat_puzzles-cat_v2 / ?aa031d83 |
| 53 | 916,428 | 1,128,450 |  |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?4485b963 / ?37e340b9 |
| 52 | 6,422,293 | 6,712,587 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?a7345b74 / ?61eb9c7e |
| 51 | 4,340,889 | 4,423,200 |  |  | ?b1d25821 / ?f151a226 |
| 51 | 8,456,372 | 8,459,598 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?fa87316a / ?34b1f957 / ?c5d05613 |
| 51 | 8,460,881 | 8,467,116 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?505f36b9 / ?34b1f957 / ?c5d05613 |
| 51 | 9,413,404 | 9,471,356 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8faea3e3 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 50 | 1,820,016 | 1,934,680 |  |  | ?e73446ab / ?db4a1678 |
| 50 | 7,543,676 | 7,563,377 |  |  | ?0046c65d / ?9fd89a83 |
| 49 | 9,414,881 | 9,471,356 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?00999396 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 48 | 4,381,840 | 4,416,426 |  |  | --cni-singleton_top_layer_v1_1 / ?82e79204 / ?679d2a21 |
| 48 | 8,538,335 | 9,463,384 |  |  | ?f1bdace5 / ?b9a55061 |
| 46 | 8,818,849 | 8,840,195 |  |  | --cni-singleton_top_layer_v1_1 / ?3a624a08 |
| 46 | 9,176,123 | 9,403,079 |  |  | ?e2945105 / ?deb62144 |
| 45 | 9,036,761 | 9,045,734 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?517564f8 / --slot_machine_rue-singleton-reserve_finalizer |
| 44 | 9,415,050 | 9,471,356 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?233afad3 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 42 | 9,412,345 | 9,445,847 | yes | SLOT_MACHINE - slot | ?95fb1d84 / --slot_machine_rue-singleton-slot |
| 40 | 916,703 | 1,127,633 |  |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?e9bf0503 / ?b11155ab |
| 40 | 8,731,906 | 8,826,431 |  |  | ?7da3909b / ?1b74f589 |
| 39 | 7,491,674 | 9,061,268 | yes | OPTION_CONTRACT - settlement payments | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-settlement_payments |
| 38 | 8,813,563 | 8,814,810 |  |  | --cni-singleton_top_layer_v1_1 / ?ec58002b |
| 38 | 9,179,161 | 9,210,288 |  |  | --cni-singleton_top_layer_v1_1 / ?32d66374 / ?e4983ff9 |
| 37 | 7,531,688 | 7,536,407 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a7a42bcb / ?d277207e / ?745f24f6 |
| 37 | 9,423,799 | 9,471,379 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d3261de1 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 37 | 9,428,549 | 9,471,257 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?19384f3d / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 36 | 8,242,557 | 8,347,303 |  |  | --cni-cat_puzzles-cat_v2 / ?9af57bf3 / ?4ba89147 |
| 35 | 9,036,761 | 9,045,731 | yes | SLOT_MACHINE - slot | ?a62dddd6 / --slot_machine_rue-singleton-slot |
| 35 | 9,422,346 | 9,471,390 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?fdaab715 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 33 | 8,815,238 | 8,818,605 |  |  | --cni-singleton_top_layer_v1_1 / ?65f68f34 |
| 32 | 8,274,724 | 8,278,766 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7334fa23 / ?34b1f957 / ?c5d05613 |
| 31 | 2,423,352 | 5,438,780 |  |  | --cni-cat_puzzles-cat_v2 / ?8390fc59 / ?2d0aeb4c |
| 31 | 6,763,718 | 7,757,297 |  |  | ?3524b909 / ?0cbe63ae |
| 31 | 8,272,402 | 8,274,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?785c0f3f / ?34b1f957 / ?c5d05613 |
| 30 | 9,412,345 | 9,445,847 | yes | FORGE - CAT reserve launcher | --cni-cat_puzzles-cat_v2 / --forge_v16-forge_reserve_launcher |
| 29 | 8,469,045 | 8,472,787 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f1c68d8f / ?34b1f957 / ?c5d05613 |
| 27 | 4,322,996 | 4,339,961 |  |  | ?23081a89 / ?f151a226 |
| 27 | 8,262,084 | 8,264,718 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3e6a8b3d / ?34b1f957 / ?c5d05613 |
| 26 | 4,323,413 | 4,408,604 |  |  | ?f7ec3e62 / ?ee28acae |
| 26 | 9,010,907 | 9,195,572 | yes | CIRCUIT - payout (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?2a3b7b00 / --circuit-circuit_puzzles-payout |
| 26 | 9,428,549 | 9,471,257 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?20f18059 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 26 | 9,432,362 | 9,471,729 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?9941c410 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 25 | 8,195,577 | 9,197,377 |  |  | --cni-cat_puzzles-cat_v2 / ?29c4bafb / ?78d7f05d |
| 25 | 9,197,468 | 9,271,248 |  |  | ?fd8f384f / ?0a74ff8f |
| 25 | 9,423,510 | 9,471,390 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?a8d33afe / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 24 | 2,073,001 | 4,760,153 |  |  | ?f1e8350c / ?7302d5c2 / --cni-did_puzzles-did_innerpuz / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 24 | 5,790,274 | 5,792,237 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / ?36892238 / ?9cac0b5b |
| 24 | 8,264,906 | 8,267,451 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?31188caf / ?34b1f957 / ?c5d05613 |
| 24 | 8,272,408 | 8,274,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?43e49151 / ?34b1f957 / ?c5d05613 |
| 24 | 9,423,348 | 9,470,790 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f6137414 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 23 | 4,719,072 | 7,687,288 |  |  | ?a9ebbf12 / ?6d79b2ea |
| 23 | 7,284,210 | 8,487,843 |  |  | --cni-singleton_top_layer_v1_1 / ?3837efe0 / ?76f5a615 |
| 23 | 9,045,884 | 9,051,181 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?394f4498 / --slot_machine_rue-singleton-reserve_finalizer |
| 23 | 9,419,196 | 9,470,818 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?9d4a0a4d / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 22 | 916,703 | 1,127,633 |  |  | ?4485b963 / ?37e340b9 |
| 22 | 6,873,326 | 6,978,020 |  |  | --cni-singleton_top_layer_v1_1 / ?86eac092 / ?a9d051d0 |
| 22 | 9,405,407 | 9,445,847 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?bb05dd2b / --slot_machine_rue-singleton-finalizer |
| 21 | 7,536,429 | 7,537,450 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1a10b650 / ?d277207e / ?745f24f6 |
| 21 | 7,537,587 | 9,217,420 |  |  | ?73ce559e / ?2d55c090 / ?58006121 |
| 21 | 7,576,728 | 9,102,175 |  |  | --cni-cat_puzzles-cat_v2 / ?069f5fcd / --streaming-stream |
| 21 | 7,973,288 | 7,977,700 |  |  | --cni-cat_puzzles-cat_v2 / ?83276e28 / ?e186ab63 / ?693e0175 |
| 21 | 8,274,927 | 8,275,408 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ca34a5ed / ?34b1f957 / ?c5d05613 |
| 21 | 9,046,925 | 9,047,215 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?a622d55c / --slot_machine_rue-singleton-reserve_finalizer |
| 21 | 9,236,083 | 9,461,427 | yes | SLOT_MACHINE - slot | ?3d9392c9 / --slot_machine_rue-singleton-slot |
| 21 | 9,422,364 | 9,471,379 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?de34702b / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 20 | 4,291,275 | 4,662,284 |  |  | --cni-singleton_top_layer_v1_1 / ?cb12785f / ?4e3b68e8 |
| 20 | 8,251,574 | 8,253,486 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3a5a3eee / ?34b1f957 / ?c5d05613 |
| 20 | 9,310,509 | 9,361,020 |  |  | --cni-cat_puzzles-cat_v2 / ?ed4648a2 / ?d744b1ce |
| 19 | 4,064,148 | 6,590,232 |  |  | ?12ce8f1a / ?51d58f8a |
| 19 | 8,168,935 | 8,170,036 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?45b83ea9 / ?34b1f957 / ?c5d05613 |
| 19 | 9,037,549 | 9,045,734 | yes | SLOT_MACHINE - slot | ?a2fe8aa1 / --slot_machine_rue-singleton-slot |
| 19 | 9,179,161 | 9,210,217 |  |  | ?c6edcbc3 / ?23d456d9 |
| 19 | 9,236,070 | 9,257,966 | yes | SLOT_MACHINE - slot | ?43388986 / --slot_machine_rue-singleton-slot |
| 18 | 1,083,230 | 1,124,907 |  |  | ?b6946b45 / ?f8763dc3 |
| 18 | 8,469,101 | 8,469,862 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f9310bed / ?34b1f957 / ?c5d05613 |
| 18 | 9,037,793 | 9,047,215 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 17 | 440,528 | 556,624 |  |  | ?bb1c4e9f / ?56b0177e / ?c87b7ff8 / ?e2ed7a8c |
| 17 | 441,434 | 556,663 |  |  | ?bb1c4e9f / ?56b0177e / ?0f963e3e / ?41deefaf |
| 17 | 2,183,800 | 2,311,203 |  |  | ?1817b177 / ?735337a9 |
| 17 | 3,560,549 | 3,575,110 | yes | TIBET_SWAP - router v1 beta | --cni-singleton_top_layer_v1_1 / --tibet_v1_beta-router |
| 17 | 7,575,833 | 9,427,213 |  |  | --cni-cat_puzzles-cat_v2 / ?b6b4a71d / --streaming-stream |
| 17 | 7,673,847 | 7,870,042 | yes | SINGLETON - multisig (m of n keys) | --cni-singleton_top_layer_v1_1 / --cni-p2_m_of_n_delegate_direct |
| 17 | 8,491,456 | 8,491,870 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d0f8281f / ?34b1f957 / ?c5d05613 |
| 17 | 8,836,297 | 8,839,178 |  |  | --cni-singleton_top_layer_v1_1 / ?4e89f644 / ?e1600321 |
| 17 | 9,037,067 | 9,045,731 | yes | SLOT_MACHINE - slot | ?0d708782 / --slot_machine_rue-singleton-slot |
| 17 | 9,045,884 | 9,051,170 | yes | SLOT_MACHINE - slot | ?7b60c9a2 / --slot_machine_rue-singleton-slot |
| 17 | 9,432,362 | 9,471,257 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d4b10227 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 16 | 7,710,028 | 9,427,238 |  |  | --cni-cat_puzzles-cat_v2 / ?374f2de2 / --streaming-stream |
| 16 | 8,262,406 | 8,264,718 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2e790d42 / ?34b1f957 / ?c5d05613 |
| 16 | 8,262,406 | 8,264,718 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b5d587ea / ?34b1f957 / ?c5d05613 |
| 16 | 8,274,936 | 8,275,408 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?46344cd4 / ?34b1f957 / ?c5d05613 |
| 15 | 1,369,247 | 2,015,283 |  |  | ?8188add5 / ?430d155b |
| 15 | 1,343,462 | 1,390,758 |  |  | --cni-singleton_top_layer / ?b215fc0a / ?68bd7ee5 |
| 15 | 8,039,818 | 8,040,447 |  |  | --cni-cat_puzzles-cat_v2 / ?367066fd / ?4741633b / ?693e0175 |
| 15 | 8,264,909 | 8,267,451 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a5ac7657 / ?34b1f957 / ?c5d05613 |
| 15 | 9,046,025 | 9,051,181 | yes | SLOT_MACHINE - slot | ?3018e622 / --slot_machine_rue-singleton-slot |
| 15 | 9,047,009 | 9,047,215 | yes | SLOT_MACHINE - slot | ?85911f0d / --slot_machine_rue-singleton-slot |
| 15 | 9,176,142 | 9,239,439 | yes | SLOT_MACHINE - state scheduler | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-state_scheduler |
| 14 | 1,115,197 | 1,138,530 |  |  | ?185c3288 / ?bf5d6386 |
| 14 | 1,154,444 | 1,374,046 |  |  | ?6fadbc18 / ?f29a630a |
| 14 | 6,968,421 | 6,978,020 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?a35bb764 / ?883058af |
| 14 | 6,968,421 | 6,978,020 |  |  | --cni-singleton_top_layer_v1_1 / ?39912fa8 / ?fa904700 |
| 14 | 8,181,626 | 8,233,068 |  |  | --cni-cat_puzzles-cat_v2 / ?5ce20349 / ?29760cd7 |
| 14 | 8,251,583 | 8,253,486 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5ef06401 / ?34b1f957 / ?c5d05613 |
| 14 | 9,436,772 | 9,470,681 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?3df9bc7b / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 13 | 710,169 | 719,608 |  |  | ?b0d9ce75 / ?2171aaa6 |
| 13 | 3,255,491 | 3,262,003 |  |  | ?28f70038 / ?b6ae628e |
| 13 | 7,544,551 | 9,194,681 |  |  | --cni-cat_puzzles-cat_v2 / ?226a3eaa / --streaming-stream |
| 12 | 724,176 | 894,714 |  |  | ?308e9343 / ?5cfa2734 |
| 12 | 1,115,530 | 1,138,530 |  |  | ?28f2c88b / ?40b3c8b7 |
| 12 | 4,305,106 | 4,314,692 |  |  | ?22f229b7 / ?796c7906 |
| 12 | 7,536,429 | 7,537,450 |  |  | ?cc5b8bc3 / ?2d55c090 / ?58006121 |
| 12 | 7,574,122 | 9,067,255 |  |  | --cni-cat_puzzles-cat_v2 / ?fab622c6 / --streaming-stream |
| 12 | 7,574,129 | 9,067,270 |  |  | --cni-cat_puzzles-cat_v2 / ?f6b6ca05 / --streaming-stream |
| 12 | 8,039,436 | 9,010,795 | yes | CIRCUIT - governance launcher (CAT_V2) | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-governance_launcher |
| 12 | 8,688,815 | 8,689,808 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8fd64b02 / --slot_machine_rue-singleton-finalizer |
| 12 | 8,837,598 | 8,839,783 |  |  | --cni-cat_puzzles-cat_v2 / ?39ec8ca9 |
| 12 | 9,436,691 | 9,466,412 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?5670203e / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 11 | 1,369,449 | 1,548,685 |  |  | ?57cc8eaa / ?06438057 |
| 11 | 2,128,785 | 4,240,138 |  |  | ?6bb67fd1 / ?339e7c3d |
| 11 | 3,255,497 | 3,263,487 |  |  | --cni-cat_puzzles-cat_v2 / ?368d5716 / ?44759ab9 |
| 11 | 3,427,617 | 7,154,178 | yes | NFT_V1 - no ownership layer, settlement payments | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-settlement_payments |
| 11 | 3,879,126 | 3,883,063 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?e574ce14 / ?fc4f0a82 |
| 11 | 5,394,263 | 9,337,557 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?7a290225 / --warp-wrapped_assets-burn_inner_puzzle |
| 11 | 8,135,314 | 8,259,827 | yes | CIRCUIT - announcer registry | ?faa2ed87 / --circuit-circuit_puzzles-announcer_registry |
| 11 | 8,831,525 | 8,835,470 |  |  | --cni-singleton_top_layer_v1_1 / ?723d36ec / ?e7d245db |
| 11 | 9,178,082 | 9,195,906 |  |  | ?6cc91652 / ?aa805750 |
| 10 | 834,768 | 852,866 |  |  | ?09cd8993 / ?83d2079d |
| 10 | 856,020 | 4,219,519 |  |  | ?0c1770bf / ?ee28acae |
| 10 | 1,543,993 | 1,548,854 |  |  | --cni-singleton_top_layer / ?98055be6 / ?aeb895fe |
| 10 | 4,864,789 | 8,111,306 |  |  | ?fc9b6a82 / ?062089cb |
| 10 | 7,540,718 | 8,244,816 |  |  | --cni-cat_puzzles-cat_v2 / ?758ebe5a / --streaming-stream |
| 10 | 8,262,398 | 8,263,224 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0e472b75 / ?34b1f957 / ?c5d05613 |
| 10 | 8,272,411 | 8,274,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c473b6f4 / ?34b1f957 / ?c5d05613 |
| 10 | 8,459,971 | 8,460,157 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0c6b6882 / ?34b1f957 / ?c5d05613 |
| 10 | 8,819,251 | 8,823,492 |  |  | --cni-singleton_top_layer_v1_1 / ?9aed44e9 / ?2576e15e |
| 10 | 8,970,062 | 9,051,931 |  |  | --cni-singleton_top_layer_v1_1 / ?50448bec / ?e572d641 |
| 10 | 9,046,925 | 9,046,957 | yes | SLOT_MACHINE - slot | ?1e1fd6af / --slot_machine_rue-singleton-slot |
| 10 | 9,177,493 | 9,197,195 |  |  | ?95d2aa19 / ?53e1d46f |
| 10 | 9,445,410 | 9,471,067 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e2275415 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 9 | 5,984,156 | 6,318,292 |  |  | ?5d0115c5 / ?fa279361 / ?17bc4080 |
| 9 | 7,977,700 | 9,007,408 |  |  | --cni-cat_puzzles-cat_v2 / --circuit-circuit_puzzles-governance_exit |
| 9 | 8,039,439 | 8,039,817 |  |  | ?343a4f7a / ?f94cfaec / ?4ba93c16 |
| 9 | 8,267,705 | 8,269,388 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e06d3eb6 / ?34b1f957 / ?c5d05613 |
| 9 | 8,249,214 | 8,251,395 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?84deeda9 / ?34b1f957 / ?c5d05613 |
| 9 | 8,823,727 | 8,937,177 |  |  | --cni-singleton_top_layer_v1_1 / ?5cfdf35c / ?e572d641 |
| 8 | 834,768 | 839,415 |  |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?ae631ee2 / ?053f68a1 |
| 8 | 1,165,352 | 1,373,636 |  |  | ?2859f5d6 / ?5c554c87 |
| 8 | 2,155,470 | 2,311,203 |  |  | --chia_blockchain_cat_v1-cat / ?8f2d5585 |
| 8 | 5,997,483 | 6,265,677 |  |  | ?826a3e53 / ?fa279361 / ?17bc4080 |
| 8 | 7,528,872 | 7,531,674 |  |  | ?565dc5ad / ?2d55c090 / ?58006121 |
| 8 | 8,265,558 | 8,267,417 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0e54c897 / ?34b1f957 / ?c5d05613 |
| 8 | 8,265,558 | 8,267,417 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bef16e50 / ?34b1f957 / ?c5d05613 |
| 8 | 8,274,982 | 8,275,408 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cda2e513 / ?34b1f957 / ?c5d05613 |
| 8 | 8,813,779 | 8,818,192 |  |  | --cni-singleton_top_layer_v1_1 / ?0f84d767 |
| 8 | 9,436,409 | 9,470,847 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?bfdc3b50 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 7 | 1,115,939 | 1,138,543 |  |  | ?9c539010 / ?03f8b1c4 |
| 7 | 5,967,627 | 5,974,644 |  |  | ?e5062551 / ?825434f7 |
| 7 | 6,394,550 | 9,387,239 |  |  | ?69f4fb04 / ?fa279361 / ?17bc4080 |
| 7 | 7,701,523 | 7,838,927 | yes | TIBET_SWAP - router v2 | --cni-singleton_top_layer_v1_1 / --tibet-v2r_router |
| 7 | 7,704,544 | 9,025,437 |  |  | --cni-cat_puzzles-cat_v2 / ?403b1389 / --streaming-stream |
| 7 | 8,039,436 | 8,040,418 | yes | CIRCUIT - announcer registry | ?d8746353 / --circuit-circuit_puzzles-announcer_registry |
| 7 | 8,230,897 | 8,975,964 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-1_of_n |
| 7 | 8,270,317 | 8,270,432 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?374b85f5 / ?34b1f957 / ?c5d05613 |
| 7 | 8,249,217 | 8,251,395 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?fc479574 / ?34b1f957 / ?c5d05613 |
| 7 | 8,251,585 | 8,253,486 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4b7293fd / ?34b1f957 / ?c5d05613 |
| 7 | 8,255,890 | 8,256,106 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e3d092f7 / ?34b1f957 / ?c5d05613 |
| 7 | 9,047,770 | 9,061,243 |  |  | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract |
| 7 | 9,445,789 | 9,470,574 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8a554e3f / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 7 | 9,445,866 | 9,449,893 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?1646cfc3 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 6 | 856,020 | 1,731,827 |  |  | ?65b47100 / ?89f600d1 |
| 6 | 832,085 | 2,249,672 |  |  | --cni-singleton_top_layer / ?ef41902d / ?ebc2069a |
| 6 | 1,165,352 | 1,371,224 |  |  | --chia_blockchain_cat_v1-cat / ?6dcdbf2a / ?4bc34f7c |
| 6 | 1,894,156 | 1,939,544 |  |  | ?d3f5c2de / ?e175c08f |
| 6 | 2,111,271 | 2,355,622 |  |  | ?fbf1521c / ?d6a71a7d |
| 6 | 2,123,088 | 2,243,839 |  |  | ?f1e8350c / ?7302d5c2 / ?31f5e810 / ?3dad4a24 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 6 | 2,269,593 | 2,279,248 |  |  | ?fc9da4dd / ?d8d3dab7 |
| 6 | 3,237,645 | 3,311,405 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?bf09d855 / ?77002b99 |
| 6 | 4,298,362 | 4,304,236 |  |  | ?431509eb / ?da6f43b3 |
| 6 | 5,392,107 | 5,394,183 | yes | WARP_GREEN - portal receiver | --cni-singleton_top_layer_v1_1 / ?a3cd6eb0 / --warp-portal_receiver |
| 6 | 7,080,473 | 7,325,466 |  |  | --cni-cat_puzzles-cat_v2 / ?f8768b42 / --streaming-stream |
| 6 | 7,075,628 | 7,079,259 |  |  | --cni-cat_puzzles-cat_v2 / ?4234cdf3 / --streaming-stream |
| 6 | 7,536,364 | 7,536,364 |  |  | ?554ebf32 / ?2d55c090 / ?58006121 |
| 6 | 7,959,327 | 7,978,062 |  |  | ?3a9b2fb9 / ?756f072d / ?4ba93c16 |
| 6 | 8,157,768 | 8,176,856 |  |  | --cni-cat_puzzles-cat_v2 / ?26bd15a5 / ?4ba89147 |
| 6 | 8,174,218 | 8,174,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?04b94f58 / ?34b1f957 / ?c5d05613 |
| 6 | 8,233,295 | 8,233,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a42ab949 / ?34b1f957 / ?c5d05613 |
| 6 | 8,233,365 | 8,233,405 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f8f365b3 / ?34b1f957 / ?c5d05613 |
| 6 | 8,233,717 | 8,233,759 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?540642ab / ?34b1f957 / ?c5d05613 |
| 6 | 8,234,093 | 8,234,138 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a3cd818f / ?34b1f957 / ?c5d05613 |
| 6 | 8,234,343 | 8,234,385 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?16302a24 / ?34b1f957 / ?c5d05613 |
| 6 | 8,234,551 | 8,234,761 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1ad0a22c / ?34b1f957 / ?c5d05613 |
| 6 | 8,235,088 | 8,235,297 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?48181de5 / ?34b1f957 / ?c5d05613 |
| 6 | 8,235,431 | 8,235,638 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c216b3a4 / ?34b1f957 / ?c5d05613 |
| 6 | 8,235,754 | 8,235,967 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?db2d19dc / ?34b1f957 / ?c5d05613 |
| 6 | 8,238,632 | 8,238,775 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?14e15b9e / ?34b1f957 / ?c5d05613 |
| 6 | 8,264,764 | 8,264,860 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d9f689da / ?34b1f957 / ?c5d05613 |
| 6 | 8,267,565 | 8,267,644 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ed66b5b9 / ?34b1f957 / ?c5d05613 |
| 6 | 8,267,709 | 8,269,386 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dd8c9f86 / ?34b1f957 / ?c5d05613 |
| 6 | 8,272,411 | 8,274,210 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2b513579 / ?34b1f957 / ?c5d05613 |
| 6 | 8,250,879 | 8,250,909 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4a948ef1 / ?34b1f957 / ?c5d05613 |
| 6 | 8,250,930 | 8,250,970 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e392b9f4 / ?34b1f957 / ?c5d05613 |
| 6 | 8,250,999 | 8,251,030 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?49595605 / ?34b1f957 / ?c5d05613 |
| 6 | 8,251,054 | 8,251,085 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c7bd3129 / ?34b1f957 / ?c5d05613 |
| 6 | 8,251,144 | 8,251,295 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?68d3c61f / ?34b1f957 / ?c5d05613 |
| 6 | 8,256,696 | 8,258,014 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?10db3783 / ?34b1f957 / ?c5d05613 |
| 6 | 8,256,775 | 8,257,134 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1af89813 / ?34b1f957 / ?c5d05613 |
| 6 | 8,660,940 | 8,660,958 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?94a79f55 / ?9121874f |
| 6 | 8,661,284 | 8,661,300 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?2b19f242 / ?9121874f |
| 6 | 8,661,330 | 8,661,360 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?88fc81b8 / ?9121874f |
| 6 | 8,684,893 | 8,685,312 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?388974ed / --slot_machine_rue-singleton-finalizer |
| 6 | 9,047,988 | 9,061,273 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / --cni-p2_1_of_n |
| 6 | 9,051,135 | 9,051,170 | yes | REWARD_DIST - CAT pay to next epoch | --cni-cat_puzzles-cat_v2 / --reward_distributor_rue-p2_next_reward_distributor_epoch |
| 5 | 1,154,467 | 1,371,114 |  |  | --chia_blockchain_cat_v1-cat / ?2859f5d6 / ?5c554c87 |
| 5 | 1,154,467 | 1,371,114 |  |  | ?6dcdbf2a / ?4bc34f7c |
| 5 | 1,889,458 | 1,889,575 |  |  | ?04bca72d / ?0eee420e |
| 5 | 2,078,394 | 2,120,587 |  |  | ?f1e8350c / ?7302d5c2 / ?3cb215c8 / ?610ef9a4 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 5 | 2,244,754 | 2,376,184 |  |  | ?7ce9095a / ?6dcc5a7c |
| 5 | 3,176,457 | 3,210,814 |  |  | ?1cb3f611 / ?cba8c217 |
| 5 | 6,272,982 | 6,278,340 |  |  | ?7c04cb1e / ?7f2d630f |
| 5 | 6,904,626 | 6,911,309 |  |  | ?fce4e3ce / ?02c3e1c3 |
| 5 | 6,450,243 | 6,450,602 |  |  | --cni-cat_puzzles-cat_v2 / ?85cd51da / ?6fb00617 / ?6db22474 / ?e409fced |
| 5 | 7,527,616 | 7,528,585 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?667b2564 / ?d277207e / ?745f24f6 |
| 5 | 7,527,616 | 7,528,585 |  |  | ?ac730546 / ?2d55c090 / ?58006121 |
| 5 | 7,528,872 | 7,531,674 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f822ee16 / ?d277207e / ?745f24f6 |
| 5 | 7,973,270 | 7,976,207 |  |  | ?da77c57d / ?5f5eb85d / ?d16bbd9e |
| 5 | 8,232,815 | 8,232,836 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?93e897c1 / ?34b1f957 / ?c5d05613 |
| 5 | 8,232,867 | 8,232,890 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?be942252 / ?34b1f957 / ?c5d05613 |
| 5 | 8,232,913 | 8,232,933 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dbbdda64 / ?34b1f957 / ?c5d05613 |
| 5 | 8,238,949 | 8,239,021 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b9151211 / ?34b1f957 / ?c5d05613 |
| 5 | 8,270,259 | 8,270,310 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bd785493 / ?34b1f957 / ?c5d05613 |
| 5 | 8,248,581 | 8,248,916 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0521921d / ?34b1f957 / ?c5d05613 |
| 5 | 8,249,439 | 8,249,488 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c49fa60b / ?34b1f957 / ?c5d05613 |
| 5 | 8,251,384 | 8,251,447 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6ffc5eb6 / ?34b1f957 / ?c5d05613 |
| 5 | 8,251,585 | 8,253,465 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?afe5030b / ?34b1f957 / ?c5d05613 |
| 5 | 8,255,648 | 8,255,866 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?92f40d34 / ?34b1f957 / ?c5d05613 |
| 5 | 8,474,325 | 8,476,813 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f026375e / ?34b1f957 / ?c5d05613 |
| 5 | 8,660,268 | 8,660,281 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?9924168e / ?9121874f |
| 5 | 8,660,913 | 8,660,925 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?13740ee2 / ?9121874f |
| 5 | 8,681,658 | 8,681,690 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?32a54e1c / --slot_machine_rue-singleton-finalizer |
| 5 | 8,689,912 | 8,689,992 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d05f7401 / --slot_machine_rue-singleton-finalizer |
| 5 | 8,690,034 | 8,690,098 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?40358b55 / --slot_machine_rue-singleton-finalizer |
| 5 | 8,690,478 | 8,690,545 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?cae0242b / --slot_machine_rue-singleton-finalizer |
| 5 | 8,690,854 | 8,690,918 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?ee4f4579 / --slot_machine_rue-singleton-finalizer |
| 5 | 8,691,033 | 8,691,098 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f35f332b / --slot_machine_rue-singleton-finalizer |
| 5 | 8,691,185 | 8,691,247 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?15b925d9 / --slot_machine_rue-singleton-finalizer |
| 5 | 8,821,471 | 8,829,672 |  |  | --cni-singleton_top_layer_v1_1 / ?7484dc18 / ?74a2efca |
| 5 | 9,066,212 | 9,088,648 |  |  | --cni-singleton_top_layer_v1_1 / ?daf84484 / ?e572d641 |
| 5 | 9,290,431 | 9,290,521 |  |  | --cni-singleton_top_layer_v1_1 / ?2d68de13 / ?ed89c0b7 |
| 5 | 9,423,139 | 9,470,494 | yes | FORGE - pool | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?dffa7a46 / --forge_v16-forge_multi_reserve_finalizer / --forge_v16-forge_reserve_amount |
| 5 | 9,240,344 | 9,252,378 |  |  | ?1f750be7 / ?5d189e69 |
| 4 | 725,359 | 725,474 |  |  | ?66dde9ca / ?94d04ba3 |
| 4 | 1,210,005 | 1,568,383 |  |  | --chia_blockchain_cat_v1-cat / --chia_blockchain_cat_v1-cat / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 4 | 1,626,471 | 1,627,392 |  |  | ?875a0163 / ?5990da54 |
| 4 | 1,745,466 | 1,748,553 |  |  | ?126780fc / ?ebd47860 |
| 4 | 1,939,835 | 1,940,401 |  |  | ?9a405a73 / ?de74cb97 |
| 4 | 2,388,472 | 2,395,149 |  |  | ?e94a1430 / ?08ea5d8b |
| 4 | 3,879,133 | 3,883,046 |  |  | --cni-singleton_top_layer_v1_1 / ?96ff17ba / ?5795cd12 |
| 4 | 3,879,151 | 3,883,063 |  |  | --cni-singleton_top_layer_v1_1 / ?e51704ab / ?41f753ce |
| 4 | 3,844,452 | 3,844,634 |  |  | ?14f89fe0 / ?dd48552d |
| 4 | 4,006,126 | 4,057,067 |  |  | ?a8dd35d9 / ?0229af3e |
| 4 | 7,536,702 | 7,537,450 |  |  | ?8c14a8f4 / ?2d55c090 / ?58006121 |
| 4 | 8,039,436 | 8,039,446 | yes | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / ?023e01ea / --circuit-circuit_puzzles-statutes |
| 4 | 8,039,473 | 8,039,480 | yes | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / ?50147816 / --circuit-circuit_puzzles-statutes |
| 4 | 8,174,578 | 8,174,816 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a0ea716e / ?34b1f957 / ?c5d05613 |
| 4 | 8,135,314 | 8,135,323 | yes | CIRCUIT - statutes | --circuit-circuit_puzzles-singleton_top_layer_isa / ?79dac5ba / --circuit-circuit_puzzles-statutes |
| 4 | 8,230,720 | 8,230,728 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1b32de5b / ?34b1f957 / ?c5d05613 |
| 4 | 8,230,785 | 8,230,793 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f5e39d2f / ?34b1f957 / ?c5d05613 |
| 4 | 8,231,168 | 8,231,182 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?99db6306 / ?34b1f957 / ?c5d05613 |
| 4 | 8,231,215 | 8,231,226 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ae2615a2 / ?34b1f957 / ?c5d05613 |
| 4 | 8,231,247 | 8,231,262 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?eb42dd86 / ?34b1f957 / ?c5d05613 |
| 4 | 8,231,285 | 8,231,300 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d29ab282 / ?34b1f957 / ?c5d05613 |
| 4 | 8,233,299 | 8,233,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?56390f28 / ?34b1f957 / ?c5d05613 |
| 4 | 8,233,368 | 8,233,405 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?94a49e22 / ?34b1f957 / ?c5d05613 |
| 4 | 8,233,719 | 8,233,759 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2af31103 / ?34b1f957 / ?c5d05613 |
| 4 | 8,234,097 | 8,234,138 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?aca57a0b / ?34b1f957 / ?c5d05613 |
| 4 | 8,234,346 | 8,234,385 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e98ef2c4 / ?34b1f957 / ?c5d05613 |
| 4 | 8,234,478 | 8,234,484 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ca578e8c / ?34b1f957 / ?c5d05613 |
| 4 | 8,234,555 | 8,234,761 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2e6d6201 / ?34b1f957 / ?c5d05613 |
| 4 | 8,235,093 | 8,235,297 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?93353f47 / ?34b1f957 / ?c5d05613 |
| 4 | 8,235,433 | 8,235,638 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9ca05035 / ?34b1f957 / ?c5d05613 |
| 4 | 8,235,757 | 8,235,967 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c39d253d / ?34b1f957 / ?c5d05613 |
| 4 | 8,238,634 | 8,238,775 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?04583a97 / ?34b1f957 / ?c5d05613 |
| 4 | 8,264,767 | 8,264,860 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8f3aa24b / ?34b1f957 / ?c5d05613 |
| 4 | 8,267,525 | 8,267,543 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c0b860b3 / ?34b1f957 / ?c5d05613 |
| 4 | 8,267,568 | 8,267,644 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?46004b90 / ?34b1f957 / ?c5d05613 |
| 4 | 8,270,319 | 8,270,432 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?385b80e6 / ?34b1f957 / ?c5d05613 |
| 4 | 8,270,862 | 8,270,998 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?33cc170f / ?34b1f957 / ?c5d05613 |
| 4 | 8,274,982 | 8,275,341 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b4779a9a / ?34b1f957 / ?c5d05613 |
| 4 | 8,247,463 | 8,247,473 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dc2dce81 / ?34b1f957 / ?c5d05613 |
| 4 | 8,247,486 | 8,247,504 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?98c6e27e / ?34b1f957 / ?c5d05613 |
| 4 | 8,249,036 | 8,249,047 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?021423a0 / ?34b1f957 / ?c5d05613 |
| 4 | 8,250,884 | 8,250,909 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a29f968a / ?34b1f957 / ?c5d05613 |
| 4 | 8,250,944 | 8,250,970 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f5b5552d / ?34b1f957 / ?c5d05613 |
| 4 | 8,251,004 | 8,251,030 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e5913346 / ?34b1f957 / ?c5d05613 |
| 4 | 8,251,057 | 8,251,085 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7a7b1c2f / ?34b1f957 / ?c5d05613 |
| 4 | 8,251,270 | 8,251,295 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?833b1018 / ?34b1f957 / ?c5d05613 |
| 4 | 8,256,700 | 8,258,014 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b3eb1b9d / ?34b1f957 / ?c5d05613 |
| 4 | 8,256,836 | 8,257,134 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?175e6dd1 / ?34b1f957 / ?c5d05613 |
| 4 | 8,256,836 | 8,257,134 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d9af68f1 / ?34b1f957 / ?c5d05613 |
| 4 | 8,688,863 | 8,689,804 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?8dced62d / ?63fff50f |
| 4 | 8,688,868 | 8,689,808 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?52c8d728 / ?63fff50f |
| 4 | 8,689,254 | 8,689,615 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d6738495 / --slot_machine_rue-singleton-finalizer |
| 4 | 8,735,033 | 9,091,925 |  |  | ?d5fba4ef / ?8607bc86 |
| 4 | 8,818,187 | 8,820,923 |  |  | --cni-singleton_top_layer_v1_1 / ?f639f26d / ?74a2efca |
| 4 | 8,819,269 | 8,823,492 |  |  | --cni-singleton_top_layer_v1_1 / ?d4603758 / ?e572d641 |
| 4 | 8,832,889 | 8,833,120 |  |  | --cni-cat_puzzles-cat_v2 / ?7e1bcab8 |
| 4 | 9,045,905 | 9,046,068 | yes | SLOT_MACHINE - slot | ?9acddb39 / --slot_machine_rue-singleton-slot |
| 4 | 9,046,103 | 9,051,071 |  |  | --cni-cat_puzzles-cat_v2 / --sdk-mips-index_wrapper / --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 4 | 9,046,944 | 9,046,957 | yes | SLOT_MACHINE - slot | ?996fe2bf / --slot_machine_rue-singleton-slot |
| 4 | 9,391,763 | 9,423,322 | yes | VAULT - vault singleton, m of n | --cni-singleton_top_layer_v1_1 / --sdk-mips-index_wrapper / --cni-mips_puzzles-architecture_puzzles-delegated_puzzle_feeder / --cni-mips_puzzles-architecture_puzzles-m_of_n |
| 3 | 1,389,971 | 1,390,758 |  |  | ?90bd67c0 / ?04d3f70b |
| 3 | 1,285,744 | 1,285,868 |  |  | ?b92a9d42 / ?25d3def6 |
| 3 | 1,604,018 | 1,661,191 |  |  | --chia_blockchain_cat_v1-cat / ?a897c8f1 / ?aaa20810 |
| 3 | 1,890,750 | 1,890,750 |  |  | ?f6745b8c / ?2875c84b |
| 3 | 2,045,590 | 2,045,663 |  |  | ?e4b11b8a / ?55d8aeab |
| 3 | 2,045,761 | 2,060,141 |  |  | ?35c77278 / ?605185ca |
| 3 | 2,171,630 | 2,230,542 |  |  | ?45ca31e4 / ?cdf47b5c |
| 3 | 2,264,392 | 4,186,277 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / ?9a6c5ff6 |
| 3 | 2,373,971 | 2,374,562 |  |  | --cni-cat_puzzles-cat_v2 / ?7ce9095a / ?6dcc5a7c |
| 3 | 3,042,843 | 3,047,572 |  |  | ?fc82fc79 / ?1078499c |
| 3 | 3,043,223 | 3,050,994 |  |  | ?b6e32301 / ?80f50d4b |
| 3 | 3,879,126 | 3,879,497 |  |  | --cni-singleton_top_layer_v1_1 / ?cd6c46fe / ?b8607a2f |
| 3 | 4,222,134 | 4,222,514 |  |  | ?47ffd450 / ?328cff6e |
| 3 | 5,613,011 | 5,613,415 |  |  | --cni-singleton_top_layer_v1_1 / ?c7f87107 / ?35a13c89 / ?9c3e14a9 |
| 3 | 5,613,011 | 5,613,415 |  |  | --cni-singleton_top_layer_v1_1 / ?1d2bcc2a / ?79136871 / ?34aa8240 |
| 3 | 5,613,011 | 5,613,415 |  |  | ?2bf436a8 / ?a31a3240 / ?dccddc29 |
| 3 | 7,531,305 | 7,531,674 |  |  | ?b13fbcec / ?2d55c090 / ?58006121 |
| 3 | 7,823,074 | 7,823,573 | yes | REWARD_DIST - CAT pay to parent (Chialisp) | --cni-cat_puzzles-cat_v2 / --reward_distributor-p2_parent_v2 / --slot_machine-default_puzzles-default_cat_maker |
| 3 | 7,959,302 | 7,973,270 |  |  | --cni-cat_puzzles-cat_v2 / ?7bdd5a13 / ?2af05f83 |
| 3 | 7,973,296 | 7,973,296 |  |  | --cni-cat_puzzles-cat_v2 / ?d2b6e29a / ?090a6fe5 / ?67dda0ac |
| 3 | 7,959,318 | 7,959,331 |  |  | --circuit-circuit_puzzles-singleton_top_layer_isa / ?96ebb985 / ?7c62fa84 / ?91a93448 |
| 3 | 8,039,825 | 8,039,825 |  |  | --cni-cat_puzzles-cat_v2 / ?1207633c / ?4ebca9a3 / ?7d1b84ae |
| 3 | 8,147,717 | 8,147,773 |  |  | --cni-singleton_top_layer_v1_1 / ?282b39d6 |
| 3 | 8,229,933 | 8,229,941 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?44cb9aa4 / ?34b1f957 / ?c5d05613 |
| 3 | 8,229,963 | 8,229,965 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9b7eaa37 / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,012 | 8,230,021 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?04fd9e5c / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,356 | 8,230,365 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5438b802 / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,376 | 8,230,383 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3b876c3c / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,426 | 8,230,430 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?73b136b6 / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,528 | 8,230,533 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5c14b662 / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,563 | 8,230,569 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6ce99c5d / ?34b1f957 / ?c5d05613 |
| 3 | 8,230,887 | 8,230,893 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5a140cfd / ?34b1f957 / ?c5d05613 |
| 3 | 8,231,114 | 8,231,123 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2d078bf0 / ?34b1f957 / ?c5d05613 |
| 3 | 8,231,135 | 8,231,145 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4054df8d / ?34b1f957 / ?c5d05613 |
| 3 | 8,231,320 | 8,231,328 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?54e6fbc1 / ?34b1f957 / ?c5d05613 |
| 3 | 8,232,817 | 8,232,836 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?79f9e180 / ?34b1f957 / ?c5d05613 |
| 3 | 8,232,871 | 8,232,890 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f06147ae / ?34b1f957 / ?c5d05613 |
| 3 | 8,232,915 | 8,232,933 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6be8d27b / ?34b1f957 / ?c5d05613 |
| 3 | 8,234,327 | 8,234,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?158a1252 / ?34b1f957 / ?c5d05613 |
| 3 | 8,234,439 | 8,234,445 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?609780d7 / ?34b1f957 / ?c5d05613 |
| 3 | 8,234,449 | 8,234,453 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?224f8045 / ?34b1f957 / ?c5d05613 |
| 3 | 8,234,495 | 8,234,502 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?de9237ba / ?34b1f957 / ?c5d05613 |
| 3 | 8,238,952 | 8,239,021 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bbf29bfa / ?34b1f957 / ?c5d05613 |
| 3 | 8,264,657 | 8,264,675 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a459fd4c / ?34b1f957 / ?c5d05613 |
| 3 | 8,267,714 | 8,269,388 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4ae657f6 / ?34b1f957 / ?c5d05613 |
| 3 | 8,270,269 | 8,270,310 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f2ca2584 / ?34b1f957 / ?c5d05613 |
| 3 | 8,272,312 | 8,272,327 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?93a7ff5d / ?34b1f957 / ?c5d05613 |
| 3 | 8,243,591 | 8,243,727 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b74e2a5d / ?34b1f957 / ?c5d05613 |
| 3 | 8,244,794 | 8,244,814 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f34023c5 / ?34b1f957 / ?c5d05613 |
| 3 | 8,247,106 | 8,247,197 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dbba8d6a / ?34b1f957 / ?c5d05613 |
| 3 | 8,247,227 | 8,247,251 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bba1088b / ?34b1f957 / ?c5d05613 |
| 3 | 8,247,276 | 8,247,304 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?67662e33 / ?34b1f957 / ?c5d05613 |
| 3 | 8,247,894 | 8,247,906 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ef807a87 / ?34b1f957 / ?c5d05613 |
| 3 | 8,247,969 | 8,247,981 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?894f8c99 / ?34b1f957 / ?c5d05613 |
| 3 | 8,248,080 | 8,248,090 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ba88421e / ?34b1f957 / ?c5d05613 |
| 3 | 8,248,105 | 8,248,117 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?069448d1 / ?34b1f957 / ?c5d05613 |
| 3 | 8,248,218 | 8,248,228 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2dcd0d92 / ?34b1f957 / ?c5d05613 |
| 3 | 8,248,535 | 8,248,545 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?30f3eea6 / ?34b1f957 / ?c5d05613 |
| 3 | 8,248,632 | 8,248,916 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8064cbf7 / ?34b1f957 / ?c5d05613 |
| 3 | 8,249,450 | 8,249,488 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?39e452c6 / ?34b1f957 / ?c5d05613 |
| 3 | 8,251,431 | 8,251,447 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?22ad285d / ?34b1f957 / ?c5d05613 |
| 3 | 8,255,664 | 8,255,866 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?89f0350b / ?34b1f957 / ?c5d05613 |
| 3 | 8,255,664 | 8,255,866 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4238158c / ?34b1f957 / ?c5d05613 |
| 3 | 8,255,900 | 8,256,074 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3b151a10 / ?34b1f957 / ?c5d05613 |
| 3 | 8,255,911 | 8,256,106 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cad4a3c7 / ?34b1f957 / ?c5d05613 |
| 3 | 8,255,911 | 8,256,106 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3b519bc0 / ?34b1f957 / ?c5d05613 |
| 3 | 8,258,042 | 8,258,082 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?21eb5ffc / ?34b1f957 / ?c5d05613 |
| 3 | 8,437,390 | 8,437,408 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?30678b54 / ?34b1f957 / ?c5d05613 |
| 3 | 8,442,279 | 8,442,290 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2c195d94 / ?34b1f957 / ?c5d05613 |
| 3 | 8,442,284 | 8,442,292 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?996a6cf3 / ?34b1f957 / ?c5d05613 |
| 3 | 8,659,544 | 8,659,557 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e0d2b327 / ?9121874f |
| 3 | 8,660,174 | 8,660,185 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d3301dff / ?9121874f |
| 3 | 8,663,075 | 8,663,316 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?7d3568d9 / ?9121874f |
| 3 | 8,681,381 | 8,681,385 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?670e0d53 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,412 | 8,681,417 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?20b930fc / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,420 | 8,681,426 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e2bf98ae / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,442 | 8,681,448 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?b6ea0489 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,453 | 8,681,457 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?c94d3989 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,536 | 8,681,540 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?cad86c07 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,617 | 8,681,623 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?7e1beb5a / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,632 | 8,681,640 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?868191a9 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,681,672 | 8,681,685 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?daae1225 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,685,209 | 8,685,262 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?26b0d083 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,688,863 | 8,688,907 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?03dd6583 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,689,692 | 8,689,738 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8b7ea2a0 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,689,936 | 8,689,982 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?31352912 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,690,051 | 8,690,094 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?1e121e15 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,690,497 | 8,690,538 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?5b3b67d5 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,690,876 | 8,690,913 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?6892e4f9 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,690,891 | 8,690,928 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?551a6855 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,691,049 | 8,691,095 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?205e019c / --slot_machine_rue-singleton-finalizer |
| 3 | 8,691,199 | 8,691,242 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f8f45976 / --slot_machine_rue-singleton-finalizer |
| 3 | 8,693,051 | 8,694,607 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?177e4a4c / --slot_machine_rue-singleton-finalizer |
| 3 | 8,827,987 | 8,828,021 |  |  | ?db918b50 / ?d25122d7 |
| 3 | 8,833,536 | 8,833,555 |  |  | --cni-cat_puzzles-cat_v2 / ?c62344d8 |
| 3 | 8,813,709 | 8,814,478 |  |  | ?497a80ce / ?13632a7e |
| 3 | 9,111,356 | 9,119,647 |  |  | ?7cd33cc8 / ?4d169937 |
| 2 | 729,579 | 729,579 |  |  | ?32562a24 / ?f8fcf99c |
| 2 | 851,356 | 851,370 |  |  | ?60e8093e / ?21dc9faf |
| 2 | 852,796 | 852,866 |  |  | ?d4596fa7 / ?b3a24b98 / ?258008f8 / ?9fe54b59 / ?537d109c |
| 2 | 812,237 | 813,158 |  |  | ?a28a5230 / ?669252a6 |
| 2 | 1,049,539 | 1,049,699 |  |  | ?a4fad646 / ?6c109150 |
| 2 | 1,211,109 | 1,211,123 |  |  | ?bb9ed2fd / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2 | 1,211,545 | 1,211,550 |  |  | ?fe8f5c74 / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 2 | 1,368,910 | 1,369,084 |  |  | ?2fce669b / ?430d155b |
| 2 | 1,368,965 | 1,369,084 |  |  | ?e69e0615 / ?baf43efc |
| 2 | 1,285,875 | 1,285,889 |  |  | ?7d4cf1a9 / ?cc68d223 |
| 2 | 1,285,929 | 1,285,956 |  |  | ?be5dc8be / ?7ef45084 |
| 2 | 1,296,679 | 1,301,337 |  |  | ?8e3dc12c / ?f0bb32cf |
| 2 | 1,898,893 | 1,939,321 |  |  | --chia_blockchain_cat_v1-cat / ?e2b898e3 |
| 2 | 1,939,740 | 1,939,740 |  |  | ?c28fa7ce / ?e4916f11 |
| 2 | 2,065,256 | 2,065,266 |  |  | ?b6725276 / ?ada50be2 |
| 2 | 2,237,844 | 2,238,550 |  |  | ?86c50811 / ?b01f2c2a |
| 2 | 2,382,288 | 2,382,925 |  |  | ?238e8e3c / ?a3107477 |
| 2 | 2,382,925 | 2,382,956 |  |  | --cni-cat_puzzles-cat_v2 / ?238e8e3c / ?a3107477 |
| 2 | 2,751,667 | 2,751,999 |  |  | ?fca5956e / ?fa279361 / ?17bc4080 |
| 2 | 3,236,659 | 3,236,659 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?b6e32301 / ?80f50d4b |
| 2 | 3,521,593 | 3,535,199 |  |  | --cni-singleton_top_layer_v1_1 / ?849d8852 / ?82d8ceb1 / --cni-vc_puzzles-eml_transfer_program_covenant_adapter / --cni-vc_puzzles-covenant_layer / ?07c85285 / --cni-vc_puzzles-eml_covenant_morpher / ?25814225 / ?3583ae1a / --cni-vc_puzzles-revocation_layer |
| 2 | 4,304,958 | 4,305,225 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / ?0b1a2cfa / ?e4ca85aa |
| 2 | 4,634,776 | 4,634,908 |  |  | ?8f4fa12f / ?6d725b2f |
| 2 | 4,520,477 | 4,520,612 |  |  | --cni-cat_puzzles-cat_v2 / ?7befae01 |
| 2 | 5,142,627 | 5,142,774 |  |  | --cni-singleton_top_layer_v1_1 / ?9ef579c4 / ?39af026b |
| 2 | 5,726,184 | 8,871,221 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?ebc5f70c / --warp-wrapped_assets-burn_inner_puzzle |
| 2 | 5,984,043 | 8,053,922 |  |  | ?3833fd5e / ?fa279361 / ?17bc4080 |
| 2 | 6,871,298 | 6,871,456 |  |  | ?05d3c008 / ?a08b8aa7 |
| 2 | 6,441,193 | 6,441,242 |  |  | ?85cd51da / ?6fb00617 / ?6db22474 / ?e409fced |
| 2 | 6,446,912 | 7,846,266 |  |  | ?1d86faf8 / ?fa279361 / ?17bc4080 |
| 2 | 7,079,608 | 7,080,859 |  |  | --cni-cat_puzzles-cat_v2 / ?92aea423 / --streaming-stream |
| 2 | 7,081,375 | 7,081,391 |  |  | --cni-cat_puzzles-cat_v2 / ?991dfa5a / --streaming-stream |
| 2 | 7,075,575 | 7,075,591 |  |  | --cni-cat_puzzles-cat_v2 / ?24b5308b / --streaming-stream |
| 2 | 7,079,338 | 7,079,348 |  |  | --cni-cat_puzzles-cat_v2 / ?8e568017 / --streaming-stream |
| 2 | 7,523,780 | 7,526,051 |  |  | --cni-cat_puzzles-cat_v2 / ?b120f20e / --streaming-stream |
| 2 | 7,822,640 | 8,226,883 |  |  | --cni-cat_puzzles-cat_v2 / ?f4bab586 / --streaming-stream |
| 2 | 7,858,346 | 9,276,591 |  |  | --cni-cat_puzzles-cat_v2 / ?83f69670 / --streaming-stream |
| 2 | 7,858,353 | 9,276,582 |  |  | --cni-cat_puzzles-cat_v2 / ?9dce6774 / --streaming-stream |
| 2 | 7,959,302 | 7,959,318 |  |  | ?0b5e1886 / ?5f5eb85d / ?d16bbd9e |
| 2 | 7,543,627 | 7,543,627 |  |  | ?016cd396 / ?c838b446 |
| 2 | 8,175,808 | 8,177,595 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f56d9137 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,606 | 8,229,608 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d4c45d55 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,639 | 8,229,642 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?64054619 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,660 | 8,229,663 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a390c616 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,683 | 8,229,686 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e123183d / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,701 | 8,229,705 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e054814d / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,714 | 8,229,717 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a33ae9e2 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,741 | 8,229,744 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?baf433c9 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,757 | 8,229,758 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2f87d9b6 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,776 | 8,229,778 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?71078f35 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,789 | 8,229,793 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1e4c0cd3 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,812 | 8,229,815 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3b00ce41 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,826 | 8,229,827 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6a9966bc / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,831 | 8,229,834 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f6050a45 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,848 | 8,229,850 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?50a2c4af / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,865 | 8,229,866 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?796deb54 / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,888 | 8,229,890 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?61263c5a / ?34b1f957 / ?c5d05613 |
| 2 | 8,229,916 | 8,229,917 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?63199b6c / ?34b1f957 / ?c5d05613 |
| 2 | 8,230,491 | 8,230,496 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?440dad8d / ?34b1f957 / ?c5d05613 |
| 2 | 8,230,721 | 8,230,728 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?66ea3801 / ?34b1f957 / ?c5d05613 |
| 2 | 8,230,786 | 8,230,793 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?92f76506 / ?34b1f957 / ?c5d05613 |
| 2 | 8,230,999 | 8,231,000 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?12753de6 / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,065 | 8,231,068 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ba5cdb98 / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,089 | 8,231,091 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dd79d87c / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,170 | 8,231,182 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e5bcdcab / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,218 | 8,231,226 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ed50a694 / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,248 | 8,231,262 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f467e628 / ?34b1f957 / ?c5d05613 |
| 2 | 8,231,289 | 8,231,300 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f9344e5c / ?34b1f957 / ?c5d05613 |
| 2 | 8,233,301 | 8,233,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?95b326be / ?34b1f957 / ?c5d05613 |
| 2 | 8,233,375 | 8,233,405 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1c4fc0dd / ?34b1f957 / ?c5d05613 |
| 2 | 8,233,720 | 8,233,759 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6282c491 / ?34b1f957 / ?c5d05613 |
| 2 | 8,234,099 | 8,234,138 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ee9966ce / ?34b1f957 / ?c5d05613 |
| 2 | 8,234,347 | 8,234,385 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bb0c1152 / ?34b1f957 / ?c5d05613 |
| 2 | 8,234,429 | 8,234,431 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e6bca47c / ?34b1f957 / ?c5d05613 |
| 2 | 8,234,480 | 8,234,484 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cba1abef / ?34b1f957 / ?c5d05613 |
| 2 | 8,234,557 | 8,234,761 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c6247734 / ?34b1f957 / ?c5d05613 |
| 2 | 8,235,094 | 8,235,297 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d680a6a4 / ?34b1f957 / ?c5d05613 |
| 2 | 8,235,436 | 8,235,638 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c27f3d62 / ?34b1f957 / ?c5d05613 |
| 2 | 8,235,760 | 8,235,967 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?932b9e44 / ?34b1f957 / ?c5d05613 |
| 2 | 8,237,313 | 8,237,315 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ec6c5ce8 / ?34b1f957 / ?c5d05613 |
| 2 | 8,237,713 | 8,237,715 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?607ce0d6 / ?34b1f957 / ?c5d05613 |
| 2 | 8,237,812 | 8,237,814 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e515085c / ?34b1f957 / ?c5d05613 |
| 2 | 8,237,842 | 8,237,845 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d438438b / ?34b1f957 / ?c5d05613 |
| 2 | 8,237,919 | 8,237,921 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?001b57b7 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,016 | 8,238,019 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7850388b / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,047 | 8,238,048 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9a029284 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,172 | 8,238,173 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5df110a5 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,271 | 8,238,278 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?80bef495 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,319 | 8,238,321 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8a32de96 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,363 | 8,238,366 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ebfe3efe / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,387 | 8,238,389 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b87d4246 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,418 | 8,238,420 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dcc2f7d2 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,462 | 8,238,463 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1df4aa57 / ?34b1f957 / ?c5d05613 |
| 2 | 8,238,635 | 8,238,775 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9e2ef191 / ?34b1f957 / ?c5d05613 |
| 2 | 8,267,536 | 8,267,543 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?93dbf2ac / ?34b1f957 / ?c5d05613 |
| 2 | 8,267,574 | 8,267,644 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ec4c796a / ?34b1f957 / ?c5d05613 |
| 2 | 8,267,714 | 8,269,388 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9d84e61f / ?34b1f957 / ?c5d05613 |
| 2 | 8,269,417 | 8,269,447 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1d0ab6da / ?34b1f957 / ?c5d05613 |
| 2 | 8,270,322 | 8,270,427 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?38015636 / ?34b1f957 / ?c5d05613 |
| 2 | 8,270,322 | 8,270,427 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f2d5b281 / ?34b1f957 / ?c5d05613 |
| 2 | 8,270,878 | 8,270,998 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f14401b8 / ?34b1f957 / ?c5d05613 |
| 2 | 8,270,878 | 8,270,998 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0369e481 / ?34b1f957 / ?c5d05613 |
| 2 | 8,244,073 | 8,244,074 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?feaddfb7 / ?34b1f957 / ?c5d05613 |
| 2 | 8,247,465 | 8,247,473 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e90d5643 / ?34b1f957 / ?c5d05613 |
| 2 | 8,247,491 | 8,247,504 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c121e803 / ?34b1f957 / ?c5d05613 |
| 2 | 8,247,557 | 8,247,559 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cc9a1004 / ?34b1f957 / ?c5d05613 |
| 2 | 8,249,026 | 8,249,029 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e09fe11a / ?34b1f957 / ?c5d05613 |
| 2 | 8,249,040 | 8,249,047 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a0636016 / ?34b1f957 / ?c5d05613 |
| 2 | 8,250,888 | 8,250,909 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?41b36439 / ?34b1f957 / ?c5d05613 |
| 2 | 8,250,952 | 8,250,970 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?32582171 / ?34b1f957 / ?c5d05613 |
| 2 | 8,251,006 | 8,251,030 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b8e34fa8 / ?34b1f957 / ?c5d05613 |
| 2 | 8,251,063 | 8,251,085 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?eb5f09a6 / ?34b1f957 / ?c5d05613 |
| 2 | 8,251,277 | 8,251,295 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?036efa4a / ?34b1f957 / ?c5d05613 |
| 2 | 8,258,031 | 8,258,038 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?50a7b9ce / ?34b1f957 / ?c5d05613 |
| 2 | 8,431,885 | 8,431,887 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a24f2170 / ?34b1f957 / ?c5d05613 |
| 2 | 8,432,198 | 8,432,200 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cbcda6dd / ?34b1f957 / ?c5d05613 |
| 2 | 8,435,655 | 8,437,701 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a6992ccc / ?34b1f957 / ?c5d05613 |
| 2 | 8,437,359 | 8,437,369 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b9694303 / ?34b1f957 / ?c5d05613 |
| 2 | 8,441,191 | 8,441,254 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9167313b / ?34b1f957 / ?c5d05613 |
| 2 | 8,442,185 | 8,442,189 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?93babe1e / ?34b1f957 / ?c5d05613 |
| 2 | 8,442,227 | 8,442,230 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4c9d3719 / ?34b1f957 / ?c5d05613 |
| 2 | 8,442,244 | 8,442,246 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?fe6e774c / ?34b1f957 / ?c5d05613 |
| 2 | 8,481,392 | 8,481,412 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7252594a / ?34b1f957 / ?c5d05613 |
| 2 | 8,492,016 | 8,492,028 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?db183576 / ?34b1f957 / ?c5d05613 |
| 2 | 8,492,270 | 8,492,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?35e49877 / ?34b1f957 / ?c5d05613 |
| 2 | 8,492,437 | 8,492,450 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3ec4cd12 / ?34b1f957 / ?c5d05613 |
| 2 | 8,495,172 | 8,495,182 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ef648449 / ?34b1f957 / ?c5d05613 |
| 2 | 8,657,478 | 8,657,482 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e6faaacf / ?9121874f |
| 2 | 8,657,638 | 8,657,639 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?11ef48b8 / ?9121874f |
| 2 | 8,657,909 | 8,657,916 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?082eb6cf / ?9121874f |
| 2 | 8,658,004 | 8,658,009 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?adfb28d1 / ?9121874f |
| 2 | 8,658,090 | 8,658,093 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?218b907c / ?9121874f |
| 2 | 8,658,311 | 8,658,313 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?c2da791b / ?9121874f |
| 2 | 8,658,373 | 8,658,377 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?6375cf0c / ?9121874f |
| 2 | 8,658,422 | 8,658,428 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f73c3dc5 / ?9121874f |
| 2 | 8,658,446 | 8,658,447 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8d9f77f2 / ?9121874f |
| 2 | 8,658,570 | 8,658,573 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?5179ad8f / ?9121874f |
| 2 | 8,658,598 | 8,658,603 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8e8130ab / ?9121874f |
| 2 | 8,658,734 | 8,658,740 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f2243181 / ?9121874f |
| 2 | 8,658,772 | 8,658,775 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?6b96c926 / ?9121874f |
| 2 | 8,659,064 | 8,659,073 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?06d92789 / ?9121874f |
| 2 | 8,659,099 | 8,659,105 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?4ebfd636 / ?9121874f |
| 2 | 8,659,165 | 8,659,167 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?b4300a46 / ?9121874f |
| 2 | 8,659,257 | 8,659,261 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?4d453f29 / ?9121874f |
| 2 | 8,659,295 | 8,659,301 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?46a2e1bf / ?9121874f |
| 2 | 8,659,324 | 8,659,330 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?03ea7c0d / ?9121874f |
| 2 | 8,659,421 | 8,659,425 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?4c86ee53 / ?9121874f |
| 2 | 8,659,458 | 8,659,460 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?b9e593f1 / ?9121874f |
| 2 | 8,659,508 | 8,659,510 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d9fbc076 / ?9121874f |
| 2 | 8,660,117 | 8,660,120 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?654e6128 / ?9121874f |
| 2 | 8,660,138 | 8,660,142 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?f0783de2 / ?9121874f |
| 2 | 8,660,232 | 8,660,236 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?265ca65b / ?9121874f |
| 2 | 8,660,272 | 8,660,279 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?860f4ecf / ?5b4289f5 |
| 2 | 8,660,275 | 8,660,281 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?1c97480a / ?5b4289f5 |
| 2 | 8,660,854 | 8,660,860 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?6c3c7615 / ?9121874f |
| 2 | 8,660,918 | 8,660,924 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?444945ed / ?5b4289f5 |
| 2 | 8,660,920 | 8,660,925 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?ad28e903 / ?5b4289f5 |
| 2 | 8,660,946 | 8,660,955 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?52dd41ec / ?5b4289f5 |
| 2 | 8,660,949 | 8,660,956 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?376b2bcc / ?5b4289f5 |
| 2 | 8,661,289 | 8,661,298 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?9f0fbe0f / ?5b4289f5 |
| 2 | 8,661,293 | 8,661,299 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?1e52137f / ?5b4289f5 |
| 2 | 8,661,338 | 8,661,346 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?f25554a4 / ?5b4289f5 |
| 2 | 8,661,340 | 8,661,358 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?c54044b7 / ?5b4289f5 |
| 2 | 8,681,195 | 8,681,201 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?8bcefe05 / --slot_machine_rue-singleton-finalizer |
| 2 | 8,681,256 | 8,681,262 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?5f283796 / --slot_machine_rue-singleton-finalizer |
| 2 | 8,681,391 | 8,681,392 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?aecd2fdb / --slot_machine_rue-singleton-finalizer |
| 2 | 8,681,672 | 8,681,687 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?571348eb / ?63fff50f |
| 2 | 8,681,680 | 8,681,690 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?255f5bf7 / ?63fff50f |
| 2 | 8,685,209 | 8,685,287 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?470ad85b / ?63fff50f |
| 2 | 8,685,211 | 8,685,312 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?c5d83504 / ?63fff50f |
| 2 | 8,688,235 | 8,688,292 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?cf454a4f / --slot_machine_rue-singleton-finalizer |
| 2 | 8,688,371 | 8,688,385 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d2d10847 / --slot_machine_rue-singleton-finalizer |
| 2 | 8,689,072 | 8,689,085 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?3f548b74 / --slot_machine_rue-singleton-finalizer |
| 2 | 8,689,936 | 8,689,987 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?62f69e07 / ?63fff50f |
| 2 | 8,689,938 | 8,689,992 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?56251ea9 / ?63fff50f |
| 2 | 8,690,051 | 8,690,096 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?0bb740c3 / ?63fff50f |
| 2 | 8,690,054 | 8,690,098 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?93da12f5 / ?63fff50f |
| 2 | 8,690,497 | 8,690,542 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?5bc217d0 / ?63fff50f |
| 2 | 8,690,503 | 8,690,545 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?403e7e63 / ?63fff50f |
| 2 | 8,690,876 | 8,690,916 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?7d047a10 / ?63fff50f |
| 2 | 8,690,877 | 8,690,918 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?a33b35a4 / ?63fff50f |
| 2 | 8,690,907 | 8,690,928 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?faf38afe / ?63fff50f |
| 2 | 8,691,049 | 8,691,097 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?83a9973d / ?63fff50f |
| 2 | 8,691,053 | 8,691,098 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?7246aa44 / ?63fff50f |
| 2 | 8,691,199 | 8,691,245 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?a279ec40 / ?63fff50f |
| 2 | 8,691,202 | 8,691,247 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?e2a69d6e / ?63fff50f |
| 2 | 8,691,346 | 8,691,353 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?d01fc52f / --slot_machine_rue-singleton-finalizer |
| 2 | 9,033,372 | 9,120,093 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?f9591e4d / --warp-wrapped_assets-burn_inner_puzzle |
| 2 | 9,033,805 | 9,033,824 |  |  | ?2204d22e / ?449001e0 |
| 2 | 9,091,933 | 9,091,954 |  |  | ?5cd883a7 / ?449001e0 |
| 2 | 8,960,296 | 8,960,691 |  |  | ?4c9a53ef / ?2d55c090 / ?58006121 |
| 2 | 9,309,854 | 9,372,991 | yes | SLOT_MACHINE - slot | ?9b7f5e78 / --slot_machine_rue-singleton-slot |
| 1 | 721,245 | 721,245 |  |  | ?a929236c / ?b4826aff |
| 1 | 858,953 | 858,953 |  |  | ?d18623b6 / ?8697f7fe |
| 1 | 813,229 | 813,229 |  |  | ?844146a2 / ?669252a6 |
| 1 | 832,594 | 832,594 |  |  | ?3459caac / ?69887148 |
| 1 | 957,399 | 957,399 |  |  | ?0c8d8b71 / ?a05aad59 |
| 1 | 1,183,712 | 1,183,712 |  |  | ?a4ab8a27 / ?d2963e0f |
| 1 | 1,186,487 | 1,186,487 |  |  | ?6b0a99a5 / ?69fcd9a0 |
| 1 | 1,210,938 | 1,210,938 |  |  | ?88443573 / ?ba7dbcc0 |
| 1 | 1,211,092 | 1,211,092 |  |  | ?bb9ed2fd / ?ba7dbcc0 |
| 1 | 1,211,142 | 1,211,142 |  |  | ?bb9ed2fd / ?ba7dbcc0 / ?bb9ed2fd / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 1,211,535 | 1,211,535 |  |  | ?fe8f5c74 / ?ba7dbcc0 |
| 1 | 1,213,331 | 1,213,331 |  |  | ?fe8f5c74 / ?ba7dbcc0 / ?fe8f5c74 / ?ba7dbcc0 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 1,168,369 | 1,168,369 |  |  | ?1e0db8c9 / ?cdbccd0d |
| 1 | 1,421,131 | 1,421,131 | yes | CAT_V1 - delegated conditions | --chia_blockchain_cat_v1-cat / --cni-p2_delegated_conditions |
| 1 | 1,340,889 | 1,340,889 |  |  | ?e043b31b / ?d880e347 |
| 1 | 1,594,642 | 1,594,642 |  |  | ?a897c8f1 / ?aaa20810 |
| 1 | 1,627,545 | 1,627,545 |  |  | ?9b1fc69e / ?75955666 |
| 1 | 1,627,790 | 1,627,790 |  |  | ?8e99f1b0 / ?2f36ddf0 |
| 1 | 1,655,989 | 1,655,989 |  |  | ?93ab0d78 / ?d64aae04 |
| 1 | 1,656,222 | 1,656,222 |  |  | ?2107650f / ?17a378de |
| 1 | 1,859,346 | 1,859,346 |  |  | --chia_blockchain_cat_v1-cat / ?a34f0d44 / ?b5e483f2 |
| 1 | 1,889,234 | 1,889,234 |  |  | ?3d4d6e23 / ?8127e18e |
| 1 | 1,889,297 | 1,889,297 |  |  | ?b868bb8d / ?8127e18e |
| 1 | 1,890,750 | 1,890,750 |  |  | ?bc25380a / ?af75cea7 |
| 1 | 1,910,826 | 1,910,826 |  |  | ?82b62400 / ?942d8dbe |
| 1 | 1,981,661 | 1,981,661 |  |  | ?921ccd15 / ?2a9a15e0 |
| 1 | 1,982,517 | 1,982,517 |  |  | ?afbaabc9 / ?bcc420ae |
| 1 | 1,991,167 | 1,991,167 |  |  | ?f1e8350c / ?7302d5c2 / ?dd8135d5 / ?610ef9a4 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 2,065,184 | 2,065,184 |  |  | ?58aa877f / ?75af1615 |
| 1 | 2,289,496 | 2,289,496 |  |  | ?00abe87b / ?aae33e1a |
| 1 | 2,243,908 | 2,243,908 |  |  | ?f1e8350c / ?7302d5c2 / ?31f5e810 / ?3dad4a24 / ?dacf3308 / ?428b8294 / ?a1d8a6b5 / ?9bf151bb / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 2,709,067 | 2,709,067 |  |  | ?d03e8266 / ?b0be96ce |
| 1 | 2,777,394 | 2,777,394 |  |  | ?cb48893e / ?ef4542d7 / ?2f6e9a02 / ?73a81660 |
| 1 | 3,051,007 | 3,051,007 |  |  | --cni-cat_puzzles-cat_v2 / ?b6e32301 / ?80f50d4b |
| 1 | 3,186,671 | 3,186,671 |  |  | ?6bb9b47e / ?e24fcd97 |
| 1 | 3,288,047 | 3,288,047 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?8390fc59 / ?2d0aeb4c |
| 1 | 3,489,715 | 3,489,715 |  |  | ?981f112a / ?fa279361 / ?17bc4080 |
| 1 | 3,511,766 | 3,511,766 |  |  | --cni-singleton_top_layer_v1_1 / ?849d8852 / ?82d8ceb1 / --cni-vc_puzzles-p2_announced_delegated_puzzle |
| 1 | 3,350,443 | 3,350,443 |  |  | ?8aeb41ef / ?fa279361 / ?17bc4080 |
| 1 | 3,470,232 | 3,470,232 |  |  | ?b11d23f3 / ?0d2ffa4d |
| 1 | 3,647,889 | 3,647,889 |  |  | --cni-singleton_top_layer_v1_1 / ?32865fb2 / ?93f5840f / ?0737418c / ?8344b9d8 |
| 1 | 3,840,433 | 3,840,433 |  |  | ?070a9cc9 / ?8adadc16 |
| 1 | 4,219,519 | 4,219,519 |  |  | ?d78ee811 / ?b6e0ad5d |
| 1 | 5,073,066 | 5,073,066 |  |  | --cni-cat_puzzles-cat_v2 / ?79bd0d65 / ?32c10874 |
| 1 | 5,076,522 | 5,076,522 |  |  | --cni-cat_puzzles-cat_v2 / ?79bd0d65 / ?32c10874 / --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 1 | 4,969,839 | 4,969,839 |  |  | ?db12e5b5 / ?b0ae243c |
| 1 | 4,970,057 | 4,970,057 |  |  | ?68edefa6 / ?69cc61ac |
| 1 | 5,491,149 | 5,491,149 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?14c9b3dd / --warp-wrapped_assets-burn_inner_puzzle |
| 1 | 5,553,181 | 5,553,181 |  |  | ?f42d2ae4 / ?fa279361 / ?17bc4080 |
| 1 | 5,785,445 | 5,785,445 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?5ad7b6f8 / --warp-wrapped_assets-burn_inner_puzzle |
| 1 | 5,892,050 | 5,892,050 |  |  | ?8a7258ea / ?fa279361 / ?17bc4080 |
| 1 | 6,103,755 | 6,103,755 |  |  | --cni-cat_puzzles-cat_v2 / ?a34bcbd3 / ?4a0285fa |
| 1 | 6,269,607 | 6,269,607 |  |  | ?8636d04a / ?2073e81b |
| 1 | 6,318,809 | 6,318,809 |  |  | ?38b874e4 / ?fa279361 / ?17bc4080 |
| 1 | 6,326,457 | 6,326,457 |  |  | ?aeb00340 / ?fa279361 / ?17bc4080 |
| 1 | 6,701,020 | 6,701,020 |  |  | ?e82e42b2 / ?53cadf71 |
| 1 | 6,904,314 | 6,904,314 |  |  | ?2168b42a / ?67f35bf3 |
| 1 | 6,904,358 | 6,904,358 |  |  | ?2e190736 / ?f00c3b79 |
| 1 | 6,904,383 | 6,904,383 |  |  | ?bfd4b81f / ?adc98018 |
| 1 | 6,904,457 | 6,904,457 |  |  | ?f0698626 / ?6375ced9 |
| 1 | 6,904,554 | 6,904,554 |  |  | ?08918edb / ?5c95bdc1 |
| 1 | 6,904,579 | 6,904,579 |  |  | ?7368c5ee / ?0f1c20a2 |
| 1 | 6,878,759 | 6,878,759 |  |  | --cni-singleton_top_layer_v1_1 / --cni-nft_puzzles-nft_state_layer / --cni-nft_puzzles-nft_ownership_layer / --cni-nft_puzzles-nft_ownership_transfer_program_one_way_claim_with_royalties / ?1931abac / ?21fef75f |
| 1 | 6,878,759 | 6,878,759 |  |  | --cni-singleton_top_layer_v1_1 / ?7ec6e32e / ?f6abb8e4 |
| 1 | 6,935,915 | 6,935,915 |  |  | ?47922463 / ?79742f9b |
| 1 | 6,804,881 | 6,804,881 |  |  | ?213a07e4 / ?fa279361 / ?17bc4080 |
| 1 | 7,080,994 | 7,080,994 |  |  | --cni-cat_puzzles-cat_v2 / ?2e2232e2 / --streaming-stream |
| 1 | 7,081,348 | 7,081,348 |  |  | --cni-cat_puzzles-cat_v2 / ?9b88d6fd / --streaming-stream |
| 1 | 7,075,506 | 7,075,506 |  |  | --cni-cat_puzzles-cat_v2 / ?e59e6650 / --streaming-stream |
| 1 | 7,075,530 | 7,075,530 |  |  | --cni-cat_puzzles-cat_v2 / ?eb67f7db / --streaming-stream |
| 1 | 7,075,553 | 7,075,553 |  |  | --cni-cat_puzzles-cat_v2 / ?be4063f0 / --streaming-stream |
| 1 | 7,079,278 | 7,079,278 |  |  | --cni-cat_puzzles-cat_v2 / ?247d80d6 / --streaming-stream |
| 1 | 7,079,545 | 7,079,545 |  |  | --cni-cat_puzzles-cat_v2 / ?8f579cf4 / --streaming-stream |
| 1 | 7,291,776 | 7,291,776 |  |  | --cni-cat_puzzles-cat_v2 / ?bd34690e / --streaming-stream |
| 1 | 7,368,670 | 7,368,670 |  |  | --cni-cat_puzzles-cat_v2 / ?47dc2757 / --streaming-stream |
| 1 | 7,603,379 | 7,603,379 |  |  | --cni-cat_puzzles-cat_v2 / ?a65f873a / --streaming-stream |
| 1 | 7,589,647 | 7,589,647 |  |  | --cni-cat_puzzles-cat_v2 / ?69ce13c3 / --streaming-stream |
| 1 | 7,560,778 | 7,560,778 |  |  | --cni-cat_puzzles-cat_v2 / ?1c5eb22b / --streaming-stream |
| 1 | 7,560,786 | 7,560,786 |  |  | --cni-cat_puzzles-cat_v2 / ?c421d67f / --streaming-stream |
| 1 | 7,560,866 | 7,560,866 |  |  | --cni-cat_puzzles-cat_v2 / ?571e6886 / --streaming-stream |
| 1 | 7,560,876 | 7,560,876 |  |  | --cni-cat_puzzles-cat_v2 / ?9cd6c018 / --streaming-stream |
| 1 | 7,561,032 | 7,561,032 |  |  | --cni-cat_puzzles-cat_v2 / ?98b86c7c / --streaming-stream |
| 1 | 7,561,076 | 7,561,076 |  |  | --cni-cat_puzzles-cat_v2 / ?7f08d815 / --streaming-stream |
| 1 | 7,574,830 | 7,574,830 |  |  | --cni-cat_puzzles-cat_v2 / ?0d339f33 / --streaming-stream |
| 1 | 7,502,235 | 7,502,235 |  |  | --cni-singleton_top_layer_v1_1 / --chip_0045-option_contract / --cni-p2_1_of_n |
| 1 | 7,709,984 | 7,709,984 |  |  | --cni-cat_puzzles-cat_v2 / ?4be7682e / --streaming-stream |
| 1 | 7,710,612 | 7,710,612 |  |  | ?25fbd0d4 / ?87a17c3e |
| 1 | 7,973,313 | 7,973,313 |  |  | --cni-cat_puzzles-cat_v2 / ?13bad167 / ?01c4c1fa / ?5b9b86da |
| 1 | 7,959,302 | 7,959,302 |  |  | --circuit-circuit_puzzles-singleton_top_layer_isa / ?8a078a99 / ?7c62fa84 / ?91a93448 |
| 1 | 7,541,987 | 7,541,987 |  |  | --cni-cat_puzzles-cat_v2 / ?f96a29e9 / --streaming-stream |
| 1 | 7,542,141 | 7,542,141 |  |  | --cni-cat_puzzles-cat_v2 / ?ad1e3c08 / --streaming-stream |
| 1 | 8,039,840 | 8,039,840 |  |  | --cni-cat_puzzles-cat_v2 / ?b5c4b835 / ?23654393 / ?5b9b86da |
| 1 | 8,166,294 | 8,166,294 |  |  | --cni-singleton_top_layer_v1_1 / ?882b6b5c |
| 1 | 8,166,701 | 8,166,701 |  |  | --cni-singleton_top_layer_v1_1 / ?95d39447 |
| 1 | 8,174,320 | 8,174,320 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f7a1bf75 / ?34b1f957 / ?c5d05613 |
| 1 | 8,174,540 | 8,174,540 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c26f5db3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,174,820 | 8,174,820 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?84fc2be4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,175,166 | 8,175,166 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?be2991ae / ?34b1f957 / ?c5d05613 |
| 1 | 8,175,354 | 8,175,354 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ec2f6c8f / ?34b1f957 / ?c5d05613 |
| 1 | 8,175,494 | 8,175,494 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?73bc2cc3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,175,537 | 8,175,537 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a1cb3078 / ?34b1f957 / ?c5d05613 |
| 1 | 8,175,808 | 8,175,808 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?47b48712 / ?34b1f957 / ?c5d05613 |
| 1 | 8,177,595 | 8,177,595 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6e8d3429 / ?34b1f957 / ?c5d05613 |
| 1 | 8,135,381 | 8,135,381 | yes | CIRCUIT - recharge auction (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?81e0cc37 / --circuit-circuit_puzzles-recharge_auction |
| 1 | 8,154,107 | 8,154,107 |  |  | --cni-cat_puzzles-cat_v2 / ?cb562430 / ?4ba89147 |
| 1 | 8,229,538 | 8,229,538 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?640e29c7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,608 | 8,229,608 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a46d766a / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,642 | 8,229,642 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?15109c7c / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,663 | 8,229,663 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6199a4fe / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,686 | 8,229,686 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a96c4924 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,705 | 8,229,705 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?16410d63 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,717 | 8,229,717 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3c1e0042 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,744 | 8,229,744 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2519ef90 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,758 | 8,229,758 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e693ee99 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,778 | 8,229,778 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ec5220cd / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,793 | 8,229,793 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4a494a72 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,815 | 8,229,815 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6cf5a18d / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,827 | 8,229,827 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1d713025 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,834 | 8,229,834 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c20dde24 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,850 | 8,229,850 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?25e1c07f / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,866 | 8,229,866 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?de4fcec4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,890 | 8,229,890 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2a20e537 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,917 | 8,229,917 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?61e9cdd3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,936 | 8,229,936 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?866bf9e8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,941 | 8,229,941 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?43c2afe6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,941 | 8,229,941 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?df92a9e9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,964 | 8,229,964 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9745ea0b / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,965 | 8,229,965 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a893bea9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,229,965 | 8,229,965 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?381a33cc / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,017 | 8,230,017 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bd1f1c85 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,021 | 8,230,021 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?741fbed6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,021 | 8,230,021 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8e0846c9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,352 | 8,230,352 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e2a5714c / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,361 | 8,230,361 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1cbf01fd / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,365 | 8,230,365 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?02df0149 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,365 | 8,230,365 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?94ce6191 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,379 | 8,230,379 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?37a1be4c / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,383 | 8,230,383 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?10e363cd / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,383 | 8,230,383 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?16c34061 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,428 | 8,230,428 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c77f5a4e / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,430 | 8,230,430 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e9e2c3e3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,430 | 8,230,430 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2f7a8378 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,496 | 8,230,496 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f969156c / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,531 | 8,230,531 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0e53f65e / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,533 | 8,230,533 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f9b4e062 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,533 | 8,230,533 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0d15c740 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,567 | 8,230,567 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a3faa92e / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,569 | 8,230,569 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a2934c4c / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,569 | 8,230,569 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?fc60c46f / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,722 | 8,230,722 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9dcf35fc / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,722 | 8,230,722 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?acfdbd2d / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,787 | 8,230,787 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d2341cd2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,787 | 8,230,787 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8a230810 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,889 | 8,230,889 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6af35e69 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,893 | 8,230,893 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a4a356bd / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,893 | 8,230,893 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8075cf90 / ?34b1f957 / ?c5d05613 |
| 1 | 8,230,962 | 8,230,962 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a8181218 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,000 | 8,231,000 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1e4a86b9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,028 | 8,231,028 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?89b2d0cc / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,068 | 8,231,068 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6a89900f / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,091 | 8,231,091 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?51ba9ed4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,117 | 8,231,117 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9ff063e1 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,123 | 8,231,123 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b745a528 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,123 | 8,231,123 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?62839a0b / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,136 | 8,231,136 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7239e837 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,145 | 8,231,145 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d569ee53 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,145 | 8,231,145 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?21f95265 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,172 | 8,231,172 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a83c574c / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,172 | 8,231,172 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a2f05e4b / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,220 | 8,231,220 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?680f0621 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,220 | 8,231,220 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d74d483b / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,255 | 8,231,255 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2bd2c852 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,255 | 8,231,255 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?92b1fd5b / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,292 | 8,231,292 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8b7e61c6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,292 | 8,231,292 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ebd158a8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,322 | 8,231,322 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?256f93cf / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,328 | 8,231,328 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a73628bd / ?34b1f957 / ?c5d05613 |
| 1 | 8,231,328 | 8,231,328 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8a5cac78 / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,821 | 8,232,821 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?846337fe / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,821 | 8,232,821 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?76c0a888 / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,874 | 8,232,874 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?09473bc2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,874 | 8,232,874 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?078d6414 / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,917 | 8,232,917 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?315bae2d / ?34b1f957 / ?c5d05613 |
| 1 | 8,232,917 | 8,232,917 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3221c5ad / ?34b1f957 / ?c5d05613 |
| 1 | 8,233,301 | 8,233,301 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?aa7ce761 / ?34b1f957 / ?c5d05613 |
| 1 | 8,233,375 | 8,233,375 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?00169130 / ?34b1f957 / ?c5d05613 |
| 1 | 8,233,720 | 8,233,720 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?10203b60 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,099 | 8,234,099 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b7c3a275 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,302 | 8,234,302 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d36ad66c / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,329 | 8,234,329 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4cd811a3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,333 | 8,234,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e7b2e533 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,333 | 8,234,333 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?27ed2e4a / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,347 | 8,234,347 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c39670a2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,431 | 8,234,431 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b091dc2f / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,442 | 8,234,442 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1641a906 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,445 | 8,234,445 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cbd3bb17 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,445 | 8,234,445 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?02972bae / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,451 | 8,234,451 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?dc9f2ba9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,453 | 8,234,453 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6c1d2a95 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,453 | 8,234,453 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0c83eba5 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,481 | 8,234,481 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0c36091a / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,481 | 8,234,481 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1a1ddf0e / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,497 | 8,234,497 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?54fd0457 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,502 | 8,234,502 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f3c85c44 / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,502 | 8,234,502 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ae211f6a / ?34b1f957 / ?c5d05613 |
| 1 | 8,234,557 | 8,234,557 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ba03f962 / ?34b1f957 / ?c5d05613 |
| 1 | 8,235,094 | 8,235,094 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bf323cfc / ?34b1f957 / ?c5d05613 |
| 1 | 8,235,436 | 8,235,436 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?84774726 / ?34b1f957 / ?c5d05613 |
| 1 | 8,235,760 | 8,235,760 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?92ddabed / ?34b1f957 / ?c5d05613 |
| 1 | 8,237,315 | 8,237,315 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e4f0ad6c / ?34b1f957 / ?c5d05613 |
| 1 | 8,237,715 | 8,237,715 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?794357b8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,237,814 | 8,237,814 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?958e1b31 / ?34b1f957 / ?c5d05613 |
| 1 | 8,237,845 | 8,237,845 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d538956b / ?34b1f957 / ?c5d05613 |
| 1 | 8,237,921 | 8,237,921 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e8d5ab1e / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,019 | 8,238,019 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?13e98589 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,048 | 8,238,048 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c1eb7221 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,173 | 8,238,173 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5fe5985c / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,278 | 8,238,278 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?16da9c5b / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,321 | 8,238,321 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?29120585 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,366 | 8,238,366 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a1c0ec36 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,389 | 8,238,389 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9508cd61 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,420 | 8,238,420 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4c7edfd4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,463 | 8,238,463 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a82ac2b6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,546 | 8,238,546 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?34b5aaf9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,635 | 8,238,635 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bc353b6a / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,955 | 8,238,955 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d2abcc71 / ?34b1f957 / ?c5d05613 |
| 1 | 8,238,955 | 8,238,955 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f7e6140a / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,672 | 8,264,672 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?27a182fd / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,675 | 8,264,675 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c3e9c9b9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,675 | 8,264,675 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7811fdad / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,780 | 8,264,780 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b43f1774 / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,780 | 8,264,780 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2dac966d / ?34b1f957 / ?c5d05613 |
| 1 | 8,264,893 | 8,264,893 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b58e08f2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,267,537 | 8,267,537 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d4699423 / ?34b1f957 / ?c5d05613 |
| 1 | 8,267,537 | 8,267,537 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?58c339b5 / ?34b1f957 / ?c5d05613 |
| 1 | 8,267,574 | 8,267,574 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6d7b50e6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,269,445 | 8,269,445 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e3ffbb9e / ?34b1f957 / ?c5d05613 |
| 1 | 8,269,447 | 8,269,447 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1a452774 / ?34b1f957 / ?c5d05613 |
| 1 | 8,270,278 | 8,270,278 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?89158f19 / ?34b1f957 / ?c5d05613 |
| 1 | 8,270,278 | 8,270,278 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?08950d39 / ?34b1f957 / ?c5d05613 |
| 1 | 8,270,876 | 8,270,876 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?af51e339 / ?34b1f957 / ?c5d05613 |
| 1 | 8,272,324 | 8,272,324 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?21f4a7f0 / ?34b1f957 / ?c5d05613 |
| 1 | 8,272,327 | 8,272,327 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6f7f3a2c / ?34b1f957 / ?c5d05613 |
| 1 | 8,272,327 | 8,272,327 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1457db2b / ?34b1f957 / ?c5d05613 |
| 1 | 8,272,354 | 8,272,354 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f735564b / ?34b1f957 / ?c5d05613 |
| 1 | 8,272,366 | 8,272,366 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?10faf197 / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,501 | 8,242,501 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4deb689f / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,510 | 8,242,510 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9bf4a437 / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,529 | 8,242,529 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ca5eac9d / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,535 | 8,242,535 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d587901a / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,564 | 8,242,564 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?84d74817 / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,566 | 8,242,566 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a844c2ef / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,678 | 8,242,678 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b3f2ebfc / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,685 | 8,242,685 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e58d885b / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,792 | 8,242,792 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d6425fd9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,797 | 8,242,797 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bb281a0c / ?34b1f957 / ?c5d05613 |
| 1 | 8,242,862 | 8,242,862 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1f49ecff / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,385 | 8,243,385 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?87171ee4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,423 | 8,243,423 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d8e96dd2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,501 | 8,243,501 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bba330ce / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,531 | 8,243,531 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?47d48805 / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,603 | 8,243,603 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ec9e29e8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,727 | 8,243,727 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7cbdbf0f / ?34b1f957 / ?c5d05613 |
| 1 | 8,243,727 | 8,243,727 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a8e715bb / ?34b1f957 / ?c5d05613 |
| 1 | 8,244,074 | 8,244,074 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6df3b573 / ?34b1f957 / ?c5d05613 |
| 1 | 8,244,080 | 8,244,080 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?70f0ce45 / ?34b1f957 / ?c5d05613 |
| 1 | 8,244,804 | 8,244,804 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?649e8eeb / ?34b1f957 / ?c5d05613 |
| 1 | 8,244,814 | 8,244,814 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9046ce34 / ?34b1f957 / ?c5d05613 |
| 1 | 8,244,814 | 8,244,814 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?960749cf / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,006 | 8,247,006 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3bd6159b / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,127 | 8,247,127 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c152201a / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,197 | 8,247,197 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3c5ffc49 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,197 | 8,247,197 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4c40e706 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,205 | 8,247,205 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b27e7aac / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,244 | 8,247,244 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a474e700 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,251 | 8,247,251 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bd9be84d / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,251 | 8,247,251 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5d95337f / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,293 | 8,247,293 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?636c303a / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,304 | 8,247,304 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0da93c43 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,304 | 8,247,304 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ebc76651 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,323 | 8,247,323 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?8332f6dc / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,467 | 8,247,467 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3437f450 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,467 | 8,247,467 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?39002d8b / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,500 | 8,247,500 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?91cddac6 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,500 | 8,247,500 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f49be1a7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,559 | 8,247,559 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7f8d0c48 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,582 | 8,247,582 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ca22d945 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,606 | 8,247,606 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4d5848b9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,627 | 8,247,627 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?4205a7d7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,660 | 8,247,660 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d2265519 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,836 | 8,247,836 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?aad8b1f3 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,903 | 8,247,903 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?b39842a7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,906 | 8,247,906 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d8fcec36 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,906 | 8,247,906 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?66191043 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,974 | 8,247,974 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d9b82ecf / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,981 | 8,247,981 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?47406dc8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,247,981 | 8,247,981 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?062e13d1 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,085 | 8,248,085 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6b778b5c / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,090 | 8,248,090 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?c28c277a / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,090 | 8,248,090 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?fc1fc90b / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,111 | 8,248,111 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?868e9860 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,117 | 8,248,117 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6d60ba74 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,117 | 8,248,117 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?836f902b / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,222 | 8,248,222 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?da8be5f5 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,228 | 8,248,228 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9ef199e9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,228 | 8,248,228 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5ad994d1 / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,539 | 8,248,539 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?517de86a / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,545 | 8,248,545 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?873fd2eb / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,545 | 8,248,545 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9a22e98e / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,640 | 8,248,640 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?3c203a6b / ?34b1f957 / ?c5d05613 |
| 1 | 8,248,640 | 8,248,640 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?737f0243 / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,029 | 8,249,029 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f40a60ec / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,041 | 8,249,041 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?2fa23c89 / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,041 | 8,249,041 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6b277a71 / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,223 | 8,249,223 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?04010c5d / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,223 | 8,249,223 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?bd3b8f7c / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,453 | 8,249,453 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cacfefb9 / ?34b1f957 / ?c5d05613 |
| 1 | 8,249,453 | 8,249,453 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a1524572 / ?34b1f957 / ?c5d05613 |
| 1 | 8,250,888 | 8,250,888 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f7b7b512 / ?34b1f957 / ?c5d05613 |
| 1 | 8,250,952 | 8,250,952 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ae9b6483 / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,006 | 8,251,006 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?266e5bfb / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,063 | 8,251,063 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f71bcd25 / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,277 | 8,251,277 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?65a81aa8 / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,353 | 8,251,353 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?0bb14804 / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,436 | 8,251,436 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d596f0d2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,251,436 | 8,251,436 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?86377275 / ?34b1f957 / ?c5d05613 |
| 1 | 8,255,657 | 8,255,657 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?59a5a0be / ?34b1f957 / ?c5d05613 |
| 1 | 8,255,876 | 8,255,876 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?99b65217 / ?34b1f957 / ?c5d05613 |
| 1 | 8,256,709 | 8,256,709 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?ed7591d7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,256,709 | 8,256,709 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?6301237b / ?34b1f957 / ?c5d05613 |
| 1 | 8,256,830 | 8,256,830 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?28395cf0 / ?34b1f957 / ?c5d05613 |
| 1 | 8,258,038 | 8,258,038 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?31690671 / ?34b1f957 / ?c5d05613 |
| 1 | 8,258,046 | 8,258,046 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?297b3cff / ?34b1f957 / ?c5d05613 |
| 1 | 8,258,082 | 8,258,082 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?60e28d3e / ?34b1f957 / ?c5d05613 |
| 1 | 8,258,082 | 8,258,082 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?552208fb / ?34b1f957 / ?c5d05613 |
| 1 | 8,376,011 | 8,376,011 |  |  | ?ea248b3d / ?4fd12e09 |
| 1 | 8,376,011 | 8,376,011 |  |  | --cni-singleton_top_layer_v1_1 / ?2fd8b817 / ?7fdb61e1 |
| 1 | 8,431,904 | 8,431,904 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?24d166cf / ?34b1f957 / ?c5d05613 |
| 1 | 8,432,172 | 8,432,172 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?12dcc65c / ?34b1f957 / ?c5d05613 |
| 1 | 8,432,179 | 8,432,179 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?1ab339d7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,433,135 | 8,433,135 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?756f63a0 / ?34b1f957 / ?c5d05613 |
| 1 | 8,433,309 | 8,433,309 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?84720999 / ?34b1f957 / ?c5d05613 |
| 1 | 8,433,339 | 8,433,339 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e5f17562 / ?34b1f957 / ?c5d05613 |
| 1 | 8,433,399 | 8,433,399 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f2723fee / ?34b1f957 / ?c5d05613 |
| 1 | 8,433,427 | 8,433,427 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?d98f8700 / ?34b1f957 / ?c5d05613 |
| 1 | 8,442,214 | 8,442,214 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9d90bf86 / ?34b1f957 / ?c5d05613 |
| 1 | 8,444,902 | 8,444,902 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?32bcb2cf / ?34b1f957 / ?c5d05613 |
| 1 | 8,444,967 | 8,444,967 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?41b7be99 / ?34b1f957 / ?c5d05613 |
| 1 | 8,460,785 | 8,460,785 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f56c7003 / ?34b1f957 / ?c5d05613 |
| 1 | 8,476,278 | 8,476,278 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?2b027bd5 / --warp-wrapped_assets-burn_inner_puzzle |
| 1 | 8,477,896 | 8,477,896 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?9765e779 / ?34b1f957 / ?c5d05613 |
| 1 | 8,478,898 | 8,478,898 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?04c884b7 / ?34b1f957 / ?c5d05613 |
| 1 | 8,479,355 | 8,479,355 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?a56ad64d / ?34b1f957 / ?c5d05613 |
| 1 | 8,504,418 | 8,504,418 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?408f1a93 / ?34b1f957 / ?c5d05613 |
| 1 | 8,506,191 | 8,506,191 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?552686af / ?34b1f957 / ?c5d05613 |
| 1 | 8,506,921 | 8,506,921 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?5e22e1b4 / ?34b1f957 / ?c5d05613 |
| 1 | 8,507,162 | 8,507,162 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?106059d5 / ?34b1f957 / ?c5d05613 |
| 1 | 8,507,380 | 8,507,380 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?e602ab8e / ?34b1f957 / ?c5d05613 |
| 1 | 8,511,446 | 8,511,446 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?7ee6df87 / ?34b1f957 / ?c5d05613 |
| 1 | 8,511,457 | 8,511,457 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?cf956d5b / ?34b1f957 / ?c5d05613 |
| 1 | 8,515,280 | 8,515,280 |  |  | --cni-singleton_top_layer_v1_1 / ?2ad6e558 / ?06e3f924 / ?f1630be2 / ?34b1f957 / ?c5d05613 |
| 1 | 8,657,271 | 8,657,271 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?804b35ef / ?9121874f |
| 1 | 8,657,436 | 8,657,436 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?efdfdce8 / ?9121874f |
| 1 | 8,658,318 | 8,658,318 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?8a1039bf / ?5b4289f5 |
| 1 | 8,658,323 | 8,658,323 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?d1f8ad64 / ?5b4289f5 |
| 1 | 8,658,358 | 8,658,358 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?6a47ab56 / ?9121874f |
| 1 | 8,658,378 | 8,658,378 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?6069fc34 / ?5b4289f5 |
| 1 | 8,658,382 | 8,658,382 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?3a61882e / ?5b4289f5 |
| 1 | 8,658,430 | 8,658,430 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?cf16b079 / ?5b4289f5 |
| 1 | 8,658,431 | 8,658,431 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?4b7a3257 / ?5b4289f5 |
| 1 | 8,658,451 | 8,658,451 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?d3f517f3 / ?5b4289f5 |
| 1 | 8,658,455 | 8,658,455 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?61762b6d / ?5b4289f5 |
| 1 | 8,658,577 | 8,658,577 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?9308ae88 / ?5b4289f5 |
| 1 | 8,658,580 | 8,658,580 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?dc8b6fec / ?5b4289f5 |
| 1 | 8,658,605 | 8,658,605 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?0568465d / ?5b4289f5 |
| 1 | 8,658,606 | 8,658,606 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?790ad6ae / ?5b4289f5 |
| 1 | 8,658,743 | 8,658,743 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?afb9d99c / ?5b4289f5 |
| 1 | 8,658,744 | 8,658,744 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?c7f240b0 / ?5b4289f5 |
| 1 | 8,658,776 | 8,658,776 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?0c7f3822 / ?5b4289f5 |
| 1 | 8,658,778 | 8,658,778 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?1ddf397a / ?5b4289f5 |
| 1 | 8,659,078 | 8,659,078 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?7cda1f5d / ?5b4289f5 |
| 1 | 8,659,081 | 8,659,081 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?d9f08454 / ?5b4289f5 |
| 1 | 8,659,109 | 8,659,109 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?ff099989 / ?5b4289f5 |
| 1 | 8,659,112 | 8,659,112 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?b3a02dbc / ?5b4289f5 |
| 1 | 8,659,169 | 8,659,169 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?23d0bc16 / ?5b4289f5 |
| 1 | 8,659,171 | 8,659,171 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?0292086a / ?5b4289f5 |
| 1 | 8,659,235 | 8,659,235 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?58e4b41b / ?9121874f |
| 1 | 8,659,263 | 8,659,263 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?0c87307d / ?5b4289f5 |
| 1 | 8,659,266 | 8,659,266 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?d59de7d6 / ?5b4289f5 |
| 1 | 8,659,304 | 8,659,304 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?63a2fe42 / ?5b4289f5 |
| 1 | 8,659,306 | 8,659,306 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?6f6d7b03 / ?5b4289f5 |
| 1 | 8,659,333 | 8,659,333 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?4726a113 / ?5b4289f5 |
| 1 | 8,659,335 | 8,659,335 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?8cc149b5 / ?5b4289f5 |
| 1 | 8,659,426 | 8,659,426 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?45572f0d / ?5b4289f5 |
| 1 | 8,659,428 | 8,659,428 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?44b6cd80 / ?5b4289f5 |
| 1 | 8,659,462 | 8,659,462 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?9b3b7661 / ?5b4289f5 |
| 1 | 8,659,465 | 8,659,465 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?c0c1e888 / ?5b4289f5 |
| 1 | 8,659,512 | 8,659,512 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?f5e98595 / ?5b4289f5 |
| 1 | 8,659,521 | 8,659,521 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?e9da6b3a / ?5b4289f5 |
| 1 | 8,659,552 | 8,659,552 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?ce0e317d / ?5b4289f5 |
| 1 | 8,659,555 | 8,659,555 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?4fef5cf3 / ?5b4289f5 |
| 1 | 8,660,121 | 8,660,121 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?dd93228a / ?5b4289f5 |
| 1 | 8,660,124 | 8,660,124 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?e6744e11 / ?5b4289f5 |
| 1 | 8,660,145 | 8,660,145 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?884ac3c8 / ?5b4289f5 |
| 1 | 8,660,152 | 8,660,152 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?5d159a7a / ?5b4289f5 |
| 1 | 8,660,177 | 8,660,177 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?4691dcac / ?5b4289f5 |
| 1 | 8,660,179 | 8,660,179 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?f46c5853 / ?5b4289f5 |
| 1 | 8,660,239 | 8,660,239 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?90953298 / ?5b4289f5 |
| 1 | 8,660,246 | 8,660,246 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?3758a75d / ?5b4289f5 |
| 1 | 8,660,864 | 8,660,864 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?73b460cd / ?5b4289f5 |
| 1 | 8,660,868 | 8,660,868 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?9786d4f7 / ?5b4289f5 |
| 1 | 8,662,949 | 8,662,949 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?b024fedc / ?9121874f |
| 1 | 8,663,039 | 8,663,039 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?462bb53e / ?5b4289f5 |
| 1 | 8,663,077 | 8,663,077 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?6bfce760 / ?5b4289f5 |
| 1 | 8,665,044 | 8,665,044 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?e9fb9558 / ?90c1004b |
| 1 | 8,681,391 | 8,681,391 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?979b573f / ?63fff50f |
| 1 | 8,681,392 | 8,681,392 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?7c77a445 / ?63fff50f |
| 1 | 8,681,420 | 8,681,420 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?7eeeaaf6 / ?63fff50f |
| 1 | 8,681,422 | 8,681,422 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?462fefa3 / ?63fff50f |
| 1 | 8,681,453 | 8,681,453 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?4f8f9261 / ?63fff50f |
| 1 | 8,681,455 | 8,681,455 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?a47221fd / ?63fff50f |
| 1 | 8,681,546 | 8,681,546 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?e408f843 / ?63fff50f |
| 1 | 8,681,546 | 8,681,546 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?9519772b / --slot_machine_rue-singleton-finalizer |
| 1 | 8,681,632 | 8,681,632 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?d5a31176 / ?63fff50f |
| 1 | 8,681,635 | 8,681,635 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?bbee8a38 / ?63fff50f |
| 1 | 8,684,703 | 8,684,703 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?bf1d4f4d / --slot_machine_rue-singleton-finalizer |
| 1 | 8,684,721 | 8,684,721 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?209d8cd7 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,688,392 | 8,688,392 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?cc2de781 / ?63fff50f |
| 1 | 8,688,392 | 8,688,392 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?fd7fb456 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,689,104 | 8,689,104 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?3f27e832 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,689,615 | 8,689,615 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?bc70ca0c / ?63fff50f |
| 1 | 8,690,907 | 8,690,907 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?ad790412 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,691,360 | 8,691,360 |  |  | --cni-cat_puzzles-cat_v2 / --slot_machine_rue-singleton-action / ?6a601cb9 / ?63fff50f |
| 1 | 8,691,360 | 8,691,360 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?39e94612 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,698,321 | 8,698,321 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?cb6843db / --slot_machine_rue-singleton-finalizer |
| 1 | 8,699,234 | 8,699,234 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?7496c7f5 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,699,350 | 8,699,350 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?eec7a04a / --slot_machine_rue-singleton-finalizer |
| 1 | 8,700,034 | 8,700,034 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?26fdbe66 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,703,161 | 8,703,161 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?a77b5ed5 / --slot_machine_rue-singleton-finalizer |
| 1 | 8,845,800 | 8,845,800 |  |  | --cni-singleton_top_layer_v1_1 / ?33e895bf |
| 1 | 8,828,752 | 8,828,752 |  |  | --cni-singleton_top_layer_v1_1 / ?089517bc |
| 1 | 8,828,822 | 8,828,822 |  |  | --cni-singleton_top_layer_v1_1 / ?d8883509 |
| 1 | 8,883,106 | 8,883,106 |  |  | ?0aaf9028 / ?ecebf418 |
| 1 | 8,748,955 | 8,748,955 |  |  | ?38a20e99 / ?d4a4a2d3 |
| 1 | 9,290,391 | 9,290,391 |  |  | ?99f7dbf9 / ?1c5274a3 |
| 1 | 8,969,048 | 8,969,048 |  |  | --cni-cat_puzzles-cat_v2 / ?5cfda7d8 / --streaming-stream |
| 1 | 9,333,881 | 9,333,881 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?beee2723 / --warp-wrapped_assets-burn_inner_puzzle |
| 1 | 9,333,881 | 9,333,881 | yes | WARP_GREEN - burn (CAT_V2) | --cni-cat_puzzles-cat_v2 / ?9fe804e8 / --warp-wrapped_assets-burn_inner_puzzle |
| 1 | 9,404,811 | 9,404,811 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?093c65f8 / --slot_machine_rue-singleton-finalizer |
| 1 | 9,387,248 | 9,387,248 |  |  | ?173dc72d / ?fa279361 / ?17bc4080 |
| 1 | 9,391,885 | 9,391,885 |  |  | --cni-singleton_top_layer_v1_1 / --slot_machine_rue-singleton-action / ?aa29d563 / --slot_machine_rue-singleton-finalizer |
| 1 | 9,379,313 | 9,379,313 |  |  | --cni-cat_puzzles-cat_v2 / ?66e3470f / ?d744b1ce |

## All with 1 layer

| spends | first | last | known | name | layers |
|---:|---:|---:|---|---|---|
| 139,166,820 | 225,698 | 9,472,275 | yes | STD TRANSACTION | --cni-p2_delegated_puzzle_or_hidden_puzzle |
| 4,109,693 | 523,048 | 9,472,275 | yes | --cni-p2_singleton_or_delayed_puzhash | --cni-p2_singleton_or_delayed_puzhash |
| 3,216,753 | 352,060 | 9,472,227 | yes | --cni-singleton_launcher | --cni-singleton_launcher |
| 1,243,422 | 2,588,801 | 9,463,384 | yes | --cni-nft_puzzles-create_nft_launcher_from_did | --cni-nft_puzzles-create_nft_launcher_from_did |
| 1,035,878 | 3,180,192 | 9,472,275 | yes | --cni-settlement_payments | --cni-settlement_payments |
| 329,083 | 3,663,922 | 9,195,775 | yes | --tibet-p2_singleton_flashloan | --tibet-p2_singleton_flashloan |
| 179,867 | 1,243,725 | 7,579,005 |  |  | ?9a6c5ff6 |
| 111,847 | 847,079 | 9,472,086 | yes | --cni-p2_delegated_conditions | --cni-p2_delegated_conditions |
| 96,243 | 2,312,322 | 9,472,205 | yes | --cni-cat_puzzles-cat_v2 | --cni-cat_puzzles-cat_v2 |
| 13,114 | 3,228,272 | 9,471,923 | yes | --cni-p2_1_of_n | --cni-p2_1_of_n |
| 10,512 | 5,392,149 | 9,467,195 | yes | --warp-bridging_puzzle | --warp-bridging_puzzle |
| 8,966 | 5,392,187 | 9,466,700 | yes | --warp-wrapped_cats-locker | --warp-wrapped_cats-locker |
| 7,924 | 5,393,871 | 9,469,852 | yes | --warp-wrapped_cats-p2_controller_puzzle_hash | --warp-wrapped_cats-p2_controller_puzzle_hash |
| 7,906 | 1,688,501 | 2,486,211 |  |  | ?7f50639a |
| 6,769 | 560,313 | 9,194,618 | yes | --cni-p2_delegated_puzzle | --cni-p2_delegated_puzzle |
| 6,059 | 5,393,871 | 9,471,668 | yes | --warp-wrapped_cats-unlocker | --warp-wrapped_cats-unlocker |
| 5,438 | 6,755,781 | 7,521,911 |  |  | ?990fc5fa |
| 5,124 | 2,767,457 | 9,412,142 | yes | --cni-notification | --cni-notification |
| 3,472 | 1,840,071 | 2,486,211 |  |  | ?18e8d787 |
| 2,374 | 2,423,224 | 8,969,688 | yes | --cni-p2_parent | --cni-p2_parent |
| 1,731 | 9,209,497 | 9,232,341 |  |  | ?d5132bfd |
| 1,620 | 5,392,107 | 9,468,854 | yes | --warp-wrapped_assets-cat_minter | --warp-wrapped_assets-cat_minter |
| 1,555 | 5,392,149 | 9,467,195 | yes | --warp-wrapped_assets-cat_burner | --warp-wrapped_assets-cat_burner |
| 1,545 | 1,146,819 | 2,490,318 | yes | --chia_blockchain_cat_v1-cat | --chia_blockchain_cat_v1-cat |
| 852 | 3,180,127 | 7,290,633 |  |  | ?911d904f |
| 563 | 3,563,949 | 3,603,036 | yes | --tibet_v1_beta-p2_singleton_flashloan | --tibet_v1_beta-p2_singleton_flashloan |
| 375 | 9,413,404 | 9,471,729 | yes | --slot_machine_rue-singleton-p2_delegated_by_singleton | --slot_machine_rue-singleton-p2_delegated_by_singleton |
| 355 | 2,751,545 | 9,440,802 | yes | --cni-p2_singleton | --cni-p2_singleton |
| 292 | 8,330,686 | 8,335,087 |  |  | ?0e26cfb6 |
| 152 | 984,533 | 9,264,287 | yes | --clvm-identity | --clvm-identity |
| 143 | 7,884,039 | 8,331,529 |  |  | ?e52ad402 |
| 119 | 1,820,016 | 8,027,986 | yes | --cni-mips_puzzles-member_puzzles-bls_member | --cni-mips_puzzles-member_puzzles-bls_member |
| 67 | 2,216,122 | 7,179,193 | yes | --cni-singleton_top_layer | --cni-singleton_top_layer |
| 66 | 8,214,868 | 8,278,732 |  |  | ?fcdf9e9c |
| 53 | 3,222,629 | 3,629,512 |  |  | ?aa031d83 |
| 53 | 8,432,172 | 8,515,280 |  |  | ?1660c5bb |
| 44 | 1,754,452 | 1,831,280 |  |  | ?7bf43764 |
| 40 | 1,988,977 | 6,906,607 |  |  | ?caf9f007 |
| 37 | 503,113 | 2,396,985 |  |  | ?4c9f17bd |
| 34 | 8,031,665 | 8,661,414 | yes | --chia_gaming-unroll_puzzle_state_channel_unrolling_v1 | --chia_gaming-unroll_puzzle_state_channel_unrolling_v1 |
| 31 | 8,188,627 | 8,196,773 |  |  | ?6016e8eb |
| 25 | 7,543,676 | 7,563,377 |  |  | ?7d3e3229 |
| 20 | 3,429,804 | 9,309,811 | yes | --cni-singleton_top_layer_v1_1 | --cni-singleton_top_layer_v1_1 |
| 16 | 9,412,345 | 9,445,847 | yes | --forge_v16-forge_reserve_launcher | --forge_v16-forge_reserve_launcher |
| 15 | 552,112 | 851,153 |  |  | ?e6f53ce9 |
| 15 | 865,324 | 930,405 |  |  | ?fbd76059 |
| 14 | 1,750,000 | 1,753,854 |  |  | ?8745cf52 |
| 14 | 8,819,695 | 8,834,492 |  |  | ?611641a4 |
| 11 | 9,031,338 | 9,453,333 |  |  | ?d9787a5d |
| 10 | 758,175 | 850,544 |  |  | ?dacc5e85 |
| 9 | 1,343,462 | 1,390,752 |  |  | ?4863d854 |
| 9 | 9,430,378 | 9,469,306 |  |  | ?75250baa |
| 8 | 7,959,302 | 8,135,347 | yes | --circuit-circuit_puzzles-statutes_launcher | --circuit-circuit_puzzles-statutes_launcher |
| 8 | 9,219,203 | 9,232,358 |  |  | ?da59c1bd |
| 8 | 9,271,461 | 9,418,974 | yes | --cni-p2_singleton_via_delegated_puzzle | --cni-p2_singleton_via_delegated_puzzle |
| 7 | 1,809,900 | 1,812,312 |  |  | ?74bb2b00 |
| 6 | 651,830 | 749,358 |  |  | ?78a3d109 |
| 6 | 6,936,077 | 6,940,237 |  |  | ?79742f9b |
| 6 | 8,208,956 | 8,211,252 |  |  | ?abc3674f |
| 6 | 8,431,887 | 8,442,292 |  |  | ?572b10cd |
| 6 | 9,420,034 | 9,456,953 | yes | --chia_gaming-clsp-unroll-unroll_puzzle_state_channel_unrolling | --chia_gaming-clsp-unroll-unroll_puzzle_state_channel_unrolling |
| 5 | 616,471 | 632,558 |  |  | ?b5cce2d5 |
| 5 | 8,297,293 | 8,298,400 |  |  | ?8ee5a394 |
| 4 | 539,737 | 6,636,200 |  |  | ?94bb8d5d |
| 4 | 9,123,622 | 9,126,042 |  |  | ?b9d288cc |
| 3 | 705,419 | 705,568 |  |  | ?dd1036e7 |
| 3 | 789,406 | 849,452 |  |  | ?02143482 |
| 3 | 882,570 | 909,275 |  |  | ?86f0c420 |
| 3 | 1,736,473 | 1,749,739 |  |  | ?e002468c |
| 3 | 8,828,193 | 8,828,321 |  |  | ?8b1c1a31 |
| 3 | 8,828,239 | 8,828,508 |  |  | ?325a427a |
| 3 | 9,109,953 | 9,110,472 |  |  | ?437f49bc |
| 2 | 660,501 | 660,563 |  |  | ?74b108cf |
| 2 | 552,126 | 721,423 |  |  | ?af34ace8 |
| 2 | 798,870 | 808,595 |  |  | ?1d97d7cc |
| 2 | 865,373 | 902,715 |  |  | ?61ab4dbf |
| 2 | 952,523 | 952,523 |  |  | ?79dafde6 |
| 2 | 1,031,280 | 1,031,315 |  |  | ?d75690d1 |
| 2 | 1,035,238 | 1,035,621 |  |  | ?fb632de6 |
| 2 | 1,256,589 | 1,256,622 |  |  | ?52154fc3 |
| 2 | 1,256,622 | 1,257,812 |  |  | ?415da373 |
| 2 | 1,257,469 | 1,257,812 |  |  | ?ad0b8496 |
| 2 | 1,709,214 | 1,709,387 |  |  | ?e4f02a98 |
| 2 | 1,809,410 | 1,809,419 |  |  | ?7e819ebc |
| 2 | 1,809,678 | 1,809,755 |  |  | ?0d63018d |
| 2 | 1,817,475 | 1,818,600 |  |  | ?c1c5194f |
| 2 | 1,818,754 | 1,818,771 |  |  | ?f85cbb61 |
| 2 | 1,831,378 | 1,831,406 |  |  | ?da49278f |
| 2 | 1,831,737 | 1,831,748 |  |  | ?7b5b6b14 |
| 2 | 4,590,166 | 4,594,115 |  |  | ?e479a73f |
| 2 | 4,597,648 | 4,603,795 |  |  | ?056e8d38 |
| 2 | 8,815,687 | 8,818,605 |  |  | ?0b3319ad |
| 2 | 9,102,969 | 9,105,586 |  |  | ?f404fe7c |
| 2 | 9,097,428 | 9,097,434 |  |  | ?b35f00e3 |
| 2 | 9,197,637 | 9,198,395 |  |  | ?b53e39fa |
| 1 | 501,393 | 501,393 |  |  | ?9a564485 |
| 1 | 645,324 | 645,324 |  |  | ?f8e45d3c |
| 1 | 660,922 | 660,922 |  |  | ?6bc43df5 |
| 1 | 661,060 | 661,060 |  |  | ?4ce50bc9 |
| 1 | 661,151 | 661,151 |  |  | ?2e016d28 |
| 1 | 661,258 | 661,258 |  |  | ?4050ff1b |
| 1 | 666,022 | 666,022 |  |  | ?3c22df91 |
| 1 | 668,563 | 668,563 |  |  | ?58603846 |
| 1 | 668,612 | 668,612 |  |  | ?014d9169 |
| 1 | 677,333 | 677,333 |  |  | ?cd4043fa |
| 1 | 684,145 | 684,145 |  |  | ?12729e41 |
| 1 | 691,286 | 691,286 |  |  | ?625e44dc |
| 1 | 692,449 | 692,449 |  |  | ?7883cdc6 |
| 1 | 692,712 | 692,712 |  |  | ?9616cbea |
| 1 | 721,686 | 721,686 |  |  | ?602e5605 |
| 1 | 730,672 | 730,672 |  |  | ?ec63c2a0 |
| 1 | 789,626 | 789,626 |  |  | ?c06e9234 |
| 1 | 952,523 | 952,523 |  |  | ?5c7b4cb9 |
| 1 | 957,399 | 957,399 |  |  | ?a3678c9a |
| 1 | 930,004 | 930,004 |  |  | ?90c2db3a |
| 1 | 930,405 | 930,405 |  |  | ?95536796 |
| 1 | 938,390 | 938,390 |  |  | ?a930d274 |
| 1 | 938,390 | 938,390 |  |  | ?5f2bce35 |
| 1 | 1,029,895 | 1,029,895 |  |  | ?58039edd |
| 1 | 1,031,156 | 1,031,156 |  |  | ?1c7ecd40 |
| 1 | 1,248,095 | 1,248,095 |  |  | ?21cf04e3 |
| 1 | 1,248,158 | 1,248,158 |  |  | ?3e85aae2 |
| 1 | 1,253,409 | 1,253,409 |  |  | ?a27b482e |
| 1 | 1,167,841 | 1,167,841 |  |  | ?9b217fef |
| 1 | 1,683,916 | 1,683,916 |  |  | ?722d2d93 |
| 1 | 1,684,941 | 1,684,941 |  |  | ?6290cec6 |
| 1 | 1,684,941 | 1,684,941 |  |  | ?4a6ddfa6 |
| 1 | 1,688,501 | 1,688,501 |  |  | ?90963599 |
| 1 | 1,754,452 | 1,754,452 |  |  | ?5c2cd006 |
| 1 | 1,754,904 | 1,754,904 |  |  | ?0b989266 |
| 1 | 1,795,973 | 1,795,973 |  |  | ?ea64451e |
| 1 | 1,805,269 | 1,805,269 |  |  | ?30f450f7 |
| 1 | 1,817,149 | 1,817,149 |  |  | ?b83a68fb |
| 1 | 1,818,543 | 1,818,543 |  |  | ?1a4045bd |
| 1 | 1,818,572 | 1,818,572 |  |  | ?631d5660 |
| 1 | 1,818,645 | 1,818,645 |  |  | ?c99d0764 |
| 1 | 1,818,710 | 1,818,710 |  |  | ?eabe4ca5 |
| 1 | 1,818,817 | 1,818,817 |  |  | ?a3945fac |
| 1 | 1,772,968 | 1,772,968 |  |  | ?19de0962 |
| 1 | 1,828,558 | 1,828,558 |  |  | ?c0cf3675 |
| 1 | 1,830,963 | 1,830,963 |  |  | ?d608aed1 |
| 1 | 1,831,058 | 1,831,058 |  |  | ?b01098f5 |
| 1 | 1,831,113 | 1,831,113 |  |  | ?c497d643 |
| 1 | 1,831,160 | 1,831,160 |  |  | ?f27618aa |
| 1 | 1,831,280 | 1,831,280 |  |  | ?159d3490 |
| 1 | 1,831,682 | 1,831,682 |  |  | ?0acd79fd |
| 1 | 2,402,292 | 2,402,292 |  |  | ?d8600a5c |
| 1 | 4,222,854 | 4,222,854 |  |  | ?dc76d857 |
| 1 | 4,700,301 | 4,700,301 |  |  | ?32506b98 |
| 1 | 6,878,572 | 6,878,572 | yes | --chip_0037-p2_eip712_message | --chip_0037-p2_eip712_message |
| 1 | 6,940,270 | 6,940,270 |  |  | ?504b5f17 |
| 1 | 7,543,627 | 7,543,627 |  |  | ?317af126 |
| 1 | 8,246,432 | 8,246,432 |  |  | ?972be78c |
| 1 | 8,298,750 | 8,298,750 |  |  | ?aa837794 |
| 1 | 8,828,239 | 8,828,239 |  |  | ?26905d2d |
| 1 | 9,165,488 | 9,165,488 |  |  | ?e413a458 |

## All not curried

| spends | first | last | known | name | layers |
|---:|---:|---:|---|---|---|
| 16,135 | 9,163,143 | 9,292,443 |  |  | not curried code d5791a20 |
| 23 | 890,881 | 9,425,923 |  |  | not curried code 6e340b9c |
| 11 | 9,372,920 | 9,433,344 |  |  | not curried code d2084937 |
| 6 | 1,062,743 | 8,184,145 |  |  | not curried code a12871fe |

## All quoted

| spends | first | last | known | name | layers |
|---:|---:|---:|---|---|---|
| 214,630 | 228,799 | 9,467,936 | yes | quoted conditions | (q . conditions) |
