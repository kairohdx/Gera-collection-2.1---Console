from gen_collection import gen_collection

if __name__ == "__main__":
    swagger_url = str(input("Digite a URL do swagger versão 2.0: "))
    output_file = str(input("Digite o nome do arquivo (collection.json): "))
    output_file = "collection.json" if not output_file else output_file
    gen_collection(swagger_url, output_file)