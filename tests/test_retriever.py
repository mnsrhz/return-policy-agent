from return_agent.retriever import build_default_retriever


def test_retriever_finds_final_sale_policy():
    retriever = build_default_retriever("policy_docs")

    results = retriever.retrieve("Can I return a final sale handbag?", top_k=3)

    assert results
    assert any(chunk.policy_id == "POLICY:FINAL_SALE_NO_RETURNS" for chunk in results)


def test_retriever_finds_shipping_fee_policy_for_wrong_size():
    retriever = build_default_retriever("policy_docs")

    results = retriever.retrieve("Is return shipping refunded for wrong size?", top_k=5)

    assert any(
        chunk.policy_id == "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"
        for chunk in results
    )


def test_retriever_finds_damaged_item_policy():
    retriever = build_default_retriever("policy_docs")

    results = retriever.retrieve("My item arrived damaged and broken", top_k=5)

    assert any(
        chunk.policy_id == "POLICY:DAMAGE_WRONG_MISSING_REVIEW"
        for chunk in results
    )


def test_retriever_finds_refund_shipping_fee_policy():
    retriever = build_default_retriever("policy_docs")

    results = retriever.retrieve("Will return shipping fees be refunded?", top_k=6)

    assert any(
        chunk.policy_id
        in {
            "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS",
            "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS",
        }
        for chunk in results
    )


def test_retriever_finds_gift_return_policy():
    retriever = build_default_retriever("policy_docs")

    results = retriever.retrieve("Can I return a gift with a gift receipt?", top_k=6)

    assert any(
        chunk.policy_id == "POLICY:GIFT_RETURN_REQUIREMENTS"
        for chunk in results
    )
