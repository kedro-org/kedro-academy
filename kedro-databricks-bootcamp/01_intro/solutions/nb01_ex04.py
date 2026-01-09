data_processing = pipeline([
    preprocess_companies_node,
    preprocess_shuttles_node,
    create_model_input_table_node,
])
