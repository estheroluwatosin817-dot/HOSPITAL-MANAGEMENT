document.addEventListener("DOMContentLoaded", () => {
  const serviceInput = document.querySelector("#service");
  const amountInput = document.querySelector("#amount");
  const calculateButton = document.querySelector("#calculateCost");

  if (!serviceInput || !amountInput || !calculateButton) {
    return;
  }

  const serviceCosts = {
    "General Consultation": 120,
    "X-Ray Scan": 220,
    "Lab Test": 175,
    "Physiotherapy": 150,
    "Emergency Care": 320,
    "Specialist Consultation": 280,
    "Surgery Fee": 1500,
    "Maternity Care": 760,
    "Vaccination": 95,
    "Health Screening": 420,
    "Dental Checkup": 210,
    "Pharmacy Supply": 85,
    "Nutrition Counseling": 160,
    "Therapy Session": 180,
  };

  calculateButton.addEventListener("click", () => {
    const service = serviceInput.value;
    const cost = serviceCosts[service] || 0;
    if (cost > 0) {
      amountInput.value = cost;
    }
  });
});
