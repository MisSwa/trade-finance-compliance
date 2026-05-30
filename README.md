Build a multi-agent AI system for trade finance compliance at a bank.


The inputs are the trade documents — things like the bill of lading, invoice, and packing list. These come as PDFs. There may also be a policy document with the bank's internal compliance rules.
The output should be a compliance report — whether the transaction is clear, needs review, or should be rejected. With reasons.


assume the compliance officer uploads the documents manually. No database integration for now


These documents contain sensitive information — company names, bank account details, transaction amounts, country of origin. Treat it as confidential financial data. Think about what you log and what you don't.


we want to see multi-agent. So think about how you break this down into specialized agents rather than one agent doing everything.


We want human in the loop. Not a fully automated system. 

When in case of low confidence fail gracefully. 

Evaluation through the langsmith.

Sucess means when the agent can accurately whether the transaction should be rejected or reeds review and if its clear. Also should be able to give a detailed response which is fully compliant. 

Speed, accuracy and compliance are the keys to be focused on