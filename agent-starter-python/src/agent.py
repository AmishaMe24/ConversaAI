import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    inference,
    function_tool,
    metrics,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from provider_search import search_providers

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class GreeterAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
            You are the Greeter agent. Start every session with a brief, friendly greeting and an offer to help.
            Quickly triage what the user needs. If the request involves finding providers (doctors, clinics, specialties,
            phone numbers, accepted insurance, languages, availability, ratings), use the provider_search tool.

            After the initial greeting, continue as a helpful assistant: be concise, avoid complex formatting or emojis,
            and provide clear answers. Ask a short clarifying question if needed before searching (e.g., city or specialty).
            """,
        )

    @function_tool
    async def provider_search(
        self,
        context: RunContext,
        *,
        city: str | None = None,
        state: str | None = None,
        specialty: str | None = None,
        name_contains: str | None = None,
        accepting_new_patients: bool | None = None,
        min_rating: float | None = None,
        insurance: str | None = None,
        language: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Search the providers directory and return matching providers.

        Use this tool for any query about providers, doctors, clinics, phone numbers,
        specialties, languages, accepted insurance, ratings, or availability.

        It supports filters such as: city, state, specialty (partial), accepting_new_patients,
        minimum rating, insurance, language, name substring, and a result limit.

        Examples:
        - Any 2 providers from Oklahoma City → {city: "Oklahoma City", limit: 2}
        - Phone numbers of doctors in Milwaukee who do general surgery →
          {city: "Milwaukee", specialty: "General Surgery", limit: 10}

        Return value is a list of providers with: full_name, specialty, phone, address,
        accepting_new_patients, rating, insurance_accepted, languages.
        """

        logger.info(
            "Provider search invoked",
            extra={
                "city": city,
                "state": state,
                "specialty": specialty,
                "name_contains": name_contains,
                "accepting_new_patients": accepting_new_patients,
                "min_rating": min_rating,
                "insurance": insurance,
                "language": language,
                "limit": limit,
            },
        )

        results = search_providers(
            city=city,
            state=state,
            specialty=specialty,
            name_contains=name_contains,
            accepting_new_patients=accepting_new_patients,
            min_rating=min_rating,
            insurance=insurance,
            language=language,
            limit=limit,
        )
        return results


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-streaming", language="en"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=GreeterAssistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()

    try:
        await session.say(
            "Hi there! I’m your assistant. I can help find healthcare providers, answer questions, and look up details like specialties, accepted insurance, languages, and phone numbers. What can I help you with today?"
        )
    except Exception:
        logger.exception("Failed to deliver proactive greeting")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
