import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { act } from "react";
import AuthGate, { useAuthSession } from "../AuthGate";
import { UNAUTHORIZED_EVENT } from "../../lib/api";
import { auth } from "../../lib/auth";

vi.mock("../../lib/auth", () => ({
  auth: {
    me: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}));

const mockedAuth = vi.mocked(auth);

const USER = { id: 7, email: "owner@example.com", display_name: "Owner" };

function WhoAmI() {
  const session = useAuthSession();
  return <span data-testid="who">{session?.user.email ?? "no-session"}</span>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthGate", () => {
  it("shows the sign-in form when there is no session", async () => {
    mockedAuth.me.mockResolvedValue(null);
    render(
      <AuthGate>
        <WhoAmI />
      </AuthGate>
    );

    // While the probe is in flight the gate must not flash the login form.
    expect(screen.getByText(/VERIFYING SESSION/)).toBeInTheDocument();

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.queryByTestId("who")).toBeNull();
  });

  it("renders its children once a session resolves", async () => {
    mockedAuth.me.mockResolvedValue(USER);
    render(
      <AuthGate>
        <WhoAmI />
      </AuthGate>
    );

    expect(await screen.findByTestId("who")).toHaveTextContent(USER.email);
    expect(screen.queryByLabelText("Email")).toBeNull();
  });

  it("returns to the form when a request reports the session is gone", async () => {
    mockedAuth.me.mockResolvedValue(USER);
    render(
      <AuthGate>
        <WhoAmI />
      </AuthGate>
    );
    expect(await screen.findByTestId("who")).toBeInTheDocument();

    // Any 401 anywhere dispatches this (see UnauthorizedError in lib/api.ts).
    act(() => {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT as string));
    });

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(screen.queryByTestId("who")).toBeNull();
  });

  it("falls back to the form instead of hanging when the probe fails", async () => {
    mockedAuth.me.mockRejectedValue(new Error("backend down"));
    render(
      <AuthGate>
        <WhoAmI />
      </AuthGate>
    );

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  });
});
