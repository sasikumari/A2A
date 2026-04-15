# NPCI Hackathon Titans – Final Presentation Script

## 🌟 The Pitch
*“Today, we are thrilled to present the **Titan Orchestration Engine**—our Phase 2 A2A Innovation Platform designed to radically accelerate the way NPCI introduces new product rules into the ecosystem. To demonstrate its power, we will use it natively to design, test, and deploy **UPI IoT Delegated Payments** for smartwatches and car dashboards—an entirely new UPI feature—straight into our running Phase 1 UPI Switch.”*

---

## Part 1: Ideation & Product Canvas (AOC Portal)
1. **Open the Dashboard:** Go to `http://localhost:5174/` (The Titan Product Builder).
2. **The Prompt:** In the main input box, paste the following prompt:
   > *"We need to introduce UPI Circle IoT delegated payments. Users should be able to link their smartwatches and car dashboards from their primary UPI app, set a mandate limit of ₹5000, and allow the IoT device to authorize autonomous payments without a PIN."*
3. **The Canvas:** 
   - Show how the AI autonomously builds the Product Canvas, breaking it down into Core Features, System Requirements, and the End-to-End User Journey.
   - Click down the **User Journey steps on the left sidebar** to see how the system automatically creates the interactive UI mockups on the simulated phone screen.

---

## Part 2: Technical Planning & Architecture Generation
1. **Approve Prototype:** Click **Approve Prototype** (👍) at the bottom left.
2. **Documents Chat Page:** Let the Titan Engine generate the Business Requirements Document (BRD) and the Technical Specification Document (TSD).
3. **Interactive AI Architecture Prompt:**
   - In this chat phase (or the canvas phase), you can show off the AI agent’s generative architecture capabilities to the judges by pasting this prompt:
   
   > **Prompt to copy for the judges:**  
   > *"Based on the approved IoT Delegated Payments canvas, can you generate a Mermaid System Architecture Diagram demonstrating how the Primary Phone, the IoT Smartwatch, the UPI Switch, and the Issuer Bank interact during the linking phase and the actual autonomous payment? Please highlight the creation of the mandate limit and the tokenized UUID exchange."*

4. **Proceed to Technical Plan:** Click **Generate Technical Orchestration Plan**.
5. **Review Manifest:** Show the code footprint analysis (the files touched, the new endpoints being generated, and the BRD/TSD specs).

---

## Part 3: Live Agent Orchestration & Verification
1. **Start Agentic Deployment:** Read through the tech plan, then click **Start Live Execution**.
2. **Live Orchestration Console:** 
   - Watch the live SSE logs as the AI Agents (Technical, Risk, Product) actively negotiate and inject the code components (like `buildPayXML` modifications) into the Phase 1 python backend.
3. **Verify Stage:** Click **Proceed to Verification**.
   - Show how the system ran test suites and validates that the new architecture passes all logic gates.
   - Click **Check Certification** to move to the Certification dashboard.

---

## Part 4: Certification & Deployment
1. **Certification Dashboard:** 
   - Explain to the judges: *"We don't just generate code; we ensure ecosystem compliance."*
   - Show the matrix for different Banks (HDFC, SBI, ICICI) and PSPs. Show the approval statuses (Infosec, Risk, Product) and the specific test case passing rates.
2. **Deploy to Production:** Click **Deploy**.
3. **Deployment Confirmation:** Wait for the green confirmation that the code is now hot-reloaded into the Phase 1 UPI Switch on port 5000.

---

## Part 5: the "Aha!" Moment — Live IoT Demo (Phase 1)
1. **Open the Production App:** Open a new browser tab to `http://localhost:5000/iot-demo`.
2. **Show the UI:**
   - Mention that this is the real Phase 1 production environment running the code the agents just injected.
   - Emphasize the **huge, real-time XML log trace** on the right side of the screen. Show the judges that there are no "Demo" or "Simulator" keywords anywhere—this is a native financial terminal.
3. **Execute the Flow:**
   - Go to the **Devices** tab.
   - Click **Pair New Device** -> select **Smartwatch**.
   - Watch the UI transition states until the watch is **Active** with a ₹5,000 mandate.
4. **Trigger the Autonomous Payment:**
   - Return to the Home map screen and click the **BPCL Versova GPS Trigger**.
   - **THE GRAND FINALE:** Draw the judges' attention to the XML log on the right. 
   - Highlight the incoming XML payload inside the log container: Show them the tags `<upi:Device>`, `<upi:Tag name="DeviceType" value="WEARABLE"/>`, and `<upi:purpose>H</upi:purpose>`.
   - Explain that the Phase 1 Switch previously rejected these tags, but because of the AI Agent’s orchestrated deployment, the backend schema validation was updated, allowing the new IoT payload to process flawlessly.

## Congratulations, Titans! You've just blown them away! 🚀

---

## 🛠️ Appendix: Full Meta-System Architecture Prompt
If you want to blow the judges' minds by generating a complete system architecture diagram of **what you actually built for this hackathon** (the Titan Orchestrator + Phase 1 Sandbox), copy and paste this exact prompt into an AI terminal (like the Technical Plan Chat):

> *"Generate a detailed, top-down Mermaid System Architecture graph of the **NPCI Titan Orchestrator (Phase 2)** integrated with our **UPI Sandbox Switch (Phase 1)** built for this hackathon.*
> 
> *Include these core components:*
> *1. **The Product Builder UI ** which acts as the unified frontend, capturing natural language prompts.*
> *2. **The Meta-AI Orchestration Layer** which reads those prompts and employs a multi-agent system (Product Agent, Risk Agent, Technical Agent) to autonomously generate mockups, TSD/BRD documents, and write backend python code.*
> *3. **The Deployment Engine**, which tracks Git state and pushes hot-reloaded code directly into the live sandbox environment.*
> *4. **The UPI Phase 1 Sandbox (Python/Flask)**, running an active Server-Sent Events (SSE) stream, validating complex XSD schemas in real-time, and hosting the mock Bank & PSP endpoints along with the new IoT Client Interface.*
> 
> *Connect these components visually to show the entire end-to-end lifecycle—from idea generation, through AI codebase alteration, to final execution inside the live UPI transaction engine."*
