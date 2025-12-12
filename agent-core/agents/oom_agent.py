from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Optional
import yaml

from tools import (
    get_oomkilled_pods,
    get_pod_details,
    get_pod_logs,
    get_pod_events,
    update_pod_resources
)
from prompts.system_prompt import SYSTEM_PROMPT


class OOMKilledAgent:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro",
                 provider: str = "gemini"):
        """
        OOMKilled 분석 에이전트를 초기화합니다.

        Args:
            api_key: LLM API 키 (OpenAI 또는 Gemini)
            model_name: 사용할 모델 이름
            provider: LLM 제공자 ('openai' 또는 'gemini')
        """
        self.provider = provider.lower()

        if self.provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0,
                convert_system_message_to_human=True
            )
        elif self.provider == "openai":
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model_name,
                temperature=0
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'gemini'")

        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_tools(self) -> List[Tool]:
        """LangChain 도구들을 생성합니다."""
        return [
            Tool(
                name="get_oomkilled_pods",
                func=get_oomkilled_pods,
                description="""Find all pods that have been OOMKilled in a namespace.
                Input: namespace (default: 'default')
                Returns: List of OOMKilled pods with their details."""
            ),
            Tool(
                name="get_pod_details",
                func=lambda x: get_pod_details(*x.split(",")),
                description="""Get detailed information about a specific pod.
                Input: 'pod_name,namespace' (e.g., 'my-pod,default')
                Returns: Pod details including resource limits and requests."""
            ),
            Tool(
                name="get_pod_logs",
                func=lambda x: get_pod_logs(*x.split(",")),
                description="""Get logs from a pod's container.
                Input: 'pod_name,container_name,namespace' (e.g., 'my-pod,app,default')
                Returns: Last 100 lines of container logs."""
            ),
            Tool(
                name="get_pod_events",
                func=lambda x: get_pod_events(*x.split(",")),
                description="""Get Kubernetes events related to a pod.
                Input: 'pod_name,namespace' (e.g., 'my-pod,default')
                Returns: List of events including OOMKilled events."""
            ),
            Tool(
                name="suggest_resource_update",
                func=lambda x: update_pod_resources(*x.split(",")),
                description="""Get information about how to update pod resources.
                Input: 'pod_name,namespace,container_name,new_memory_limit'
                (e.g., 'my-pod,default,app,512Mi')
                Returns: Instructions and YAML for updating resources."""
            )
        ]

    def _create_agent(self) -> AgentExecutor:
        """LangChain 에이전트를 생성합니다."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )

    def analyze_oomkilled_pods(self, namespace: str = "default") -> str:
        """특정 네임스페이스의 OOMKilled 파드들을 분석합니다."""
        query = f"""
        Please analyze all OOMKilled pods in the '{namespace}' namespace.

        For each OOMKilled pod:
        1. Get the pod details to see current resource limits
        2. Check the pod events to understand when and why it was OOMKilled
        3. Review the logs to identify memory usage patterns
        4. Provide a diagnosis with recommended memory limits

        Summarize your findings and recommendations.
        """

        result = self.agent.invoke({"input": query})
        return result["output"]

    def analyze_specific_pod(self, pod_name: str, namespace: str = "default") -> str:
        """특정 파드의 OOMKilled 이슈를 분석합니다."""
        query = f"""
        Analyze the OOMKilled issue for pod '{pod_name}' in namespace '{namespace}'.

        Steps:
        1. Get detailed information about the pod
        2. Check events to see OOMKilled occurrences
        3. Review recent logs for memory allocation patterns
        4. Provide diagnosis and recommend appropriate memory limits

        Be specific with your recommendations.
        """

        result = self.agent.invoke({"input": query})
        return result["output"]

    def get_fix_instructions(self, pod_name: str, namespace: str = "default",
                            container_name: str = None, new_memory: str = None) -> str:
        """OOMKilled 이슈를 해결하기 위한 구체적인 지침을 제공합니다."""
        if not container_name or not new_memory:
            query = f"""
            I need to fix the OOMKilled issue for pod '{pod_name}' in namespace '{namespace}'.

            Please:
            1. Analyze the pod to determine which container needs more memory
            2. Calculate the appropriate memory limit based on current usage and restart patterns
            3. Provide specific instructions on how to update the Deployment

            Give me actionable steps to fix this issue.
            """
        else:
            query = f"""
            I want to update the memory limit for container '{container_name}'
            in pod '{pod_name}' (namespace: '{namespace}') to '{new_memory}'.

            Please:
            1. Get the current Deployment configuration
            2. Show me exactly what changes to make
            3. Provide the commands to apply the changes
            """

        result = self.agent.invoke({"input": query})
        return result["output"]
