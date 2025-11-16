import undetected_chromedriver as uc
import time

try:
    print("Iniciando Chrome com undetected-chromedriver...")
    driver = uc.Chrome(use_subprocess=True)
    print("Chrome iniciado com sucesso!")
    
    driver.get("https://www.google.com")
    print("Google carregado!")
    
    time.sleep(3)
    input("Pressione ENTER para fechar...")
    driver.quit()
    
except Exception as e:
    print(f"Erro: {e}")